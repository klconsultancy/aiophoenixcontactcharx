"""Unit tests for the low-level register decoding helpers in client.py.

These functions are pure (no I/O) so they run without any Modbus connection.
"""

import logging
import pytest
from aiophoenixcontactcharx.models import ErrorCode, ModemRegistration, ModemSignalQuality, ReleaseMode, VehicleStatus
from aiophoenixcontactcharx.registers import cp_register
from aiophoenixcontactcharx.client import (
    _ascii,
    _decode_cp_config,
    _decode_cp_status_and_control,
    _decode_device_info,
    _ip,
    _mac,
    _maybe_phase_current,
    _s32,
    _s64,
    _u32,
    _u64,
    _vehicle_status,
)
from tests.helpers import cp_cfg_regs, cp_status_regs, global_regs


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


# ---------------------------------------------------------------------------
# _decode_device_info
# ---------------------------------------------------------------------------

class TestDecodeDeviceInfo:
    def test_designation(self):
        assert _decode_device_info(global_regs()).designation == "CHARX TEST"

    def test_software_version(self):
        assert _decode_device_info(global_regs()).software_version == "1.9.0"

    def test_num_controllers(self):
        assert _decode_device_info(global_regs()).num_controllers == 2

    def test_mac_eth0(self):
        assert _decode_device_info(global_regs()).mac_eth0 == "AA:BB:CC:DD:EE:FF"

    def test_ip_eth0(self):
        assert _decode_device_info(global_regs()).ip_eth0 == "192.168.1.10"

    def test_subnet_eth0(self):
        assert _decode_device_info(global_regs()).subnet_eth0 == "255.255.255.0"

    def test_subnet_eth1(self):
        assert _decode_device_info(global_regs()).subnet_eth1 == "255.255.0.0"

    def test_gateway_eth0(self):
        assert _decode_device_info(global_regs()).gateway_eth0 == "192.168.1.1"

    def test_modem_registration(self):
        assert _decode_device_info(global_regs()).modem_registration == ModemRegistration.REGISTERED

    def test_modem_signal_quality(self):
        assert _decode_device_info(global_regs()).modem_signal_quality == ModemSignalQuality.GOOD

    def test_group_active_power(self):
        assert _decode_device_info(global_regs()).group_active_power_w == pytest.approx(11000.0, rel=1e-3)

    def test_group_current_l1(self):
        assert _decode_device_info(global_regs()).group_current_l1_a == pytest.approx(16.0, rel=1e-3)

    def test_group_current_l2_unknown(self):
        assert _decode_device_info(global_regs()).group_current_l2_a is None

    def test_group_current_l3_unknown(self):
        assert _decode_device_info(global_regs()).group_current_l3_a is None

    def test_availability_and_dynamic_current(self):
        info = _decode_device_info(global_regs())
        assert info.availability is True
        assert info.dynamic_max_current_a == 16


# ---------------------------------------------------------------------------
# _decode_cp_config
# ---------------------------------------------------------------------------

class TestDecodeCpConfig:
    def test_max_and_min_current(self):
        config = _decode_cp_config(1, cp_cfg_regs())
        assert config.max_current_cfg_a == 32
        assert config.min_current_cfg_a == 6

    def test_release_mode(self):
        assert _decode_cp_config(1, cp_cfg_regs()).release_mode == ReleaseMode.MODBUS

    def test_charging_point_passed_through(self):
        assert _decode_cp_config(3, cp_cfg_regs()).charging_point == 3

    def test_defaults_for_zero_registers(self):
        config = _decode_cp_config(1, [0] * 24)
        assert config.interface_config == 0
        assert config.rcm_configured is False


# ---------------------------------------------------------------------------
# _decode_cp_status_and_control
# ---------------------------------------------------------------------------

class TestDecodeCpStatusAndControl:
    def test_voltage_l1(self):
        status, _ = _decode_cp_status_and_control(1, cp_status_regs())
        assert status.voltage_l1_v == pytest.approx(230.0, rel=1e-3)

    def test_current_l1_and_l2_unknown(self):
        status, _ = _decode_cp_status_and_control(1, cp_status_regs())
        assert status.current_l1_a == pytest.approx(16.0, rel=1e-3)
        assert status.current_l2_a is None

    def test_active_power(self):
        status, _ = _decode_cp_status_and_control(1, cp_status_regs())
        assert status.active_power_w == pytest.approx(3680.0, rel=1e-3)

    def test_energy_and_session_energy(self):
        status, _ = _decode_cp_status_and_control(1, cp_status_regs())
        assert status.energy_active_wh == 123_456
        assert status.session_energy_wh == 5_000

    def test_vehicle_status_is_enum_member(self):
        status, _ = _decode_cp_status_and_control(1, cp_status_regs())
        assert status.vehicle_status == VehicleStatus.C2
        assert isinstance(status.vehicle_status, VehicleStatus)

    def test_error_code_zero(self):
        status, _ = _decode_cp_status_and_control(1, cp_status_regs())
        assert status.error_code == ErrorCode(0)

    def test_error_code_upper_word_bits(self):
        regs = cp_status_regs()
        mask = ErrorCode.CP_ERROR | ErrorCode.PP_ERROR  # bits 18–19, upper word
        regs[61] = (int(mask) >> 16) & 0xFFFF
        regs[62] = int(mask) & 0xFFFF
        status, _ = _decode_cp_status_and_control(1, regs)
        assert ErrorCode.CP_ERROR in status.error_code
        assert ErrorCode.PP_ERROR in status.error_code

    def test_error_code_lower_word_bits(self):
        regs = cp_status_regs()
        mask = ErrorCode.TEMPERATURE_TOO_HIGH | ErrorCode.RFID_READER_ERROR  # bits 0 and 6, lower word
        regs[61] = (int(mask) >> 16) & 0xFFFF
        regs[62] = int(mask) & 0xFFFF
        status, _ = _decode_cp_status_and_control(1, regs)
        assert ErrorCode.TEMPERATURE_TOO_HIGH in status.error_code
        assert ErrorCode.RFID_READER_ERROR in status.error_code

    def test_control_fields(self):
        _, control = _decode_cp_status_and_control(1, cp_status_regs())
        assert control.charging_release is True
        assert control.max_current_a == 16
        assert control.available is True
        assert control.watchdog_timer_s == 65535

    def test_charging_point_passed_through(self):
        status, control = _decode_cp_status_and_control(2, cp_status_regs())
        assert status.charging_point == 2
        assert control.charging_point == 2
