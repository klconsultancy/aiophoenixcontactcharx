"""Unit tests for the low-level register decoding helpers in client.py.

These functions are pure (no I/O) so they run without any Modbus connection.
"""

import logging
import pytest
from aiophoenixcontactcharx.models import VehicleStatus
from aiophoenixcontactcharx.registers import cp_register
from aiophoenixcontactcharx.client import (
    _ascii,
    _ip,
    _mac,
    _maybe_phase_current,
    _s32,
    _s64,
    _u32,
    _u64,
    _vehicle_status,
)


# ---------------------------------------------------------------------------
# _u32 / _s32
# ---------------------------------------------------------------------------

class TestU32:
    def test_zero(self):
        assert _u32([0, 0], 0) == 0

    def test_max(self):
        assert _u32([0xFFFF, 0xFFFF], 0) == 0xFFFFFFFF

    def test_typical_power(self):
        # 11000 W = 11_000_000 mW = 0x00A7D8C0
        mw = 11_000_000
        hi = (mw >> 16) & 0xFFFF
        lo = mw & 0xFFFF
        assert _u32([hi, lo], 0) == mw

    def test_offset(self):
        regs = [0xDEAD, 0x0001, 0x0002, 0xBEEF]
        assert _u32(regs, 1) == 0x00010002


class TestS32:
    def test_positive(self):
        # 230_000 mV = 0x00038270
        mv = 230_000
        hi = (mv >> 16) & 0xFFFF
        lo = mv & 0xFFFF
        assert _s32([hi, lo], 0) == mv

    def test_negative_minus_one(self):
        assert _s32([0xFFFF, 0xFFFF], 0) == -1

    def test_negative_reactive_power(self):
        value = -5_000_000  # -5000 W reactive
        unsigned = value & 0xFFFFFFFF
        hi = (unsigned >> 16) & 0xFFFF
        lo = unsigned & 0xFFFF
        assert _s32([hi, lo], 0) == value

    def test_zero(self):
        assert _s32([0, 0], 0) == 0


# ---------------------------------------------------------------------------
# _u64 / _s64
# ---------------------------------------------------------------------------

class TestU64:
    def test_zero(self):
        assert _u64([0, 0, 0, 0], 0) == 0

    def test_100_kwh(self):
        # 100 kWh = 100_000 Wh
        wh = 100_000
        regs = [0, 0, (wh >> 16) & 0xFFFF, wh & 0xFFFF]
        assert _u64(regs, 0) == wh

    def test_large_lifetime_energy(self):
        # 5 GWh = 5_000_000_000 Wh — needs more than 32 bits
        wh = 5_000_000_000
        w0 = (wh >> 48) & 0xFFFF
        w1 = (wh >> 32) & 0xFFFF
        w2 = (wh >> 16) & 0xFFFF
        w3 = wh & 0xFFFF
        assert _u64([w0, w1, w2, w3], 0) == wh

    def test_offset(self):
        regs = [0xAAAA, 0, 0, 0, 0, 0xBBBB]
        assert _u64(regs, 1) == 0


class TestS64:
    def test_positive(self):
        assert _s64([0, 0, 0, 42], 0) == 42

    def test_negative_minus_one(self):
        assert _s64([0xFFFF, 0xFFFF, 0xFFFF, 0xFFFF], 0) == -1

    def test_negative_varh(self):
        value = -100_000  # -100 kVARh
        unsigned = value & 0xFFFFFFFFFFFFFFFF
        w0 = (unsigned >> 48) & 0xFFFF
        w1 = (unsigned >> 32) & 0xFFFF
        w2 = (unsigned >> 16) & 0xFFFF
        w3 = unsigned & 0xFFFF
        assert _s64([w0, w1, w2, w3], 0) == value


# ---------------------------------------------------------------------------
# _ascii
# ---------------------------------------------------------------------------

class TestAscii:
    def test_two_chars_per_word(self):
        # "AB" = 0x4142
        assert _ascii([0x4142], 0, 1) == "AB"

    def test_device_designation(self):
        # "CHARX SEC-3000" padded with nulls — 10 words = 20 chars
        text = "CHARX SEC-3"
        words = []
        chars = list(text.ljust(20, "\x00"))
        for i in range(0, 20, 2):
            words.append((ord(chars[i]) << 8) | ord(chars[i + 1]))
        assert _ascii(words, 0, 10).startswith("CHARX SEC-3")

    def test_strips_null_and_whitespace(self):
        # "1.9.0   " with trailing nulls
        words = [
            (ord("1") << 8) | ord("."),
            (ord("9") << 8) | ord("."),
            (ord("0") << 8) | 0x00,
            0x0000,
        ]
        assert _ascii(words, 0, 4) == "1.9.0"

    def test_empty_registers(self):
        assert _ascii([0x0000, 0x0000], 0, 2) == ""

    def test_offset_respected(self):
        # First word is garbage, second is "AB"
        assert _ascii([0xDEAD, 0x4142], 1, 1) == "AB"


# ---------------------------------------------------------------------------
# _vehicle_status
# ---------------------------------------------------------------------------

class TestVehicleStatus:
    @pytest.mark.parametrize("code,expected", [
        (0x4131, VehicleStatus.A1),
        (0x4132, VehicleStatus.A2),
        (0x4231, VehicleStatus.B1),
        (0x4232, VehicleStatus.B2),
        (0x4331, VehicleStatus.C1),
        (0x4332, VehicleStatus.C2),
        (0x4431, VehicleStatus.D1),
        (0x4432, VehicleStatus.D2),
        (0x4530, VehicleStatus.E0),
        (0x4630, VehicleStatus.F0),
        (0x494E, VehicleStatus.IN),
    ])
    def test_all_iec_states(self, code, expected):
        assert _vehicle_status(code) == expected

    def test_null_falls_back_to_a1(self):
        assert _vehicle_status(0x0000) == VehicleStatus.A1

    def test_string_equality_preserved(self):
        assert _vehicle_status(0x4332) == "C2"

    def test_unrecognised_code_returns_in_and_logs_warning(self, caplog):
        with caplog.at_level(logging.WARNING, logger="aiophoenixcontactcharx.client"):
            result = _vehicle_status(0x5858)  # "XX" — not a valid IEC code
        assert result == VehicleStatus.IN
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "WARNING"
        assert "XX" in caplog.records[0].message


# ---------------------------------------------------------------------------
# _ip
# ---------------------------------------------------------------------------

class TestIp:
    def test_typical(self):
        assert _ip([192, 168, 1, 100], 0) == "192.168.1.100"

    def test_offset(self):
        regs = [0, 10, 0, 0, 1]
        assert _ip(regs, 1) == "10.0.0.1"


# ---------------------------------------------------------------------------
# _mac
# ---------------------------------------------------------------------------

class TestMac:
    def test_typical(self):
        # AA:BB:CC:DD:EE:FF
        regs = [0xAABB, 0xCCDD, 0xEEFF]
        assert _mac(regs, 0) == "AA:BB:CC:DD:EE:FF"

    def test_zeros(self):
        assert _mac([0, 0, 0], 0) == "00:00:00:00:00:00"

    def test_offset(self):
        regs = [0xDEAD, 0x0102, 0x0304, 0x0506]
        assert _mac(regs, 1) == "01:02:03:04:05:06"


# ---------------------------------------------------------------------------
# _maybe_phase_current
# ---------------------------------------------------------------------------

class TestMaybePhaseCurrentSentinel:
    def test_minus_one_returns_none(self):
        assert _maybe_phase_current([0xFFFF, 0xFFFF], 0) is None

    def test_zero_returns_zero(self):
        assert _maybe_phase_current([0, 0], 0) == 0

    def test_normal_value(self):
        # 16 A = 16_000 mA = 0x00003E80
        ma = 16_000
        hi = (ma >> 16) & 0xFFFF
        lo = ma & 0xFFFF
        assert _maybe_phase_current([hi, lo], 0) == ma


# ---------------------------------------------------------------------------
# cp_register
# ---------------------------------------------------------------------------

class TestCpRegister:
    def test_cp1_offset_299(self):
        assert cp_register(1, 299) == 1299

    def test_cp12_offset_100(self):
        assert cp_register(12, 100) == 12100

    def test_cp12_boundary(self):
        assert cp_register(12, 300) == 12300

    def test_cp13_raises(self):
        with pytest.raises(ValueError, match="1–12"):
            cp_register(13, 299)

    def test_cp0_raises(self):
        with pytest.raises(ValueError, match="1–12"):
            cp_register(0, 299)

    def test_cp49_raises(self):
        with pytest.raises(ValueError, match="1–12"):
            cp_register(49, 299)
