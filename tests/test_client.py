"""Unit tests for CharxClient — all Modbus I/O is mocked."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from aiophoenixcontactcharx import (
    CharxClient,
    CharxConnectionError,
    CharxModbusError,
)
from aiophoenixcontactcharx.models import (
    EnergyMeterType,
    ModemRegistration,
    ModemSignalQuality,
    ReleaseMode,
    TempMonitoring,
)


# ---------------------------------------------------------------------------
# Helpers to build realistic register arrays
# ---------------------------------------------------------------------------

def _global_regs() -> list[int]:
    """68 registers (100–167) with recognisable values for assertions."""
    regs = [0] * 68
    # designation: "CHARX TEST  " (10 words = 20 chars)
    text = "CHARX TEST          "
    for i, idx in enumerate(range(0, 10)):
        regs[idx] = (ord(text[i * 2]) << 8) | ord(text[i * 2 + 1])
    # SW version: "1.9.0   " (4 words)
    sw = "1.9.0   "
    for i in range(4):
        regs[10 + i] = (ord(sw[i * 2]) << 8) | ord(sw[i * 2 + 1])
    regs[14] = 2          # num_controllers
    # MAC ETH0: AA:BB:CC:DD:EE:FF
    regs[15] = 0xAABB
    regs[16] = 0xCCDD
    regs[17] = 0xEEFF
    # IP ETH0: 192.168.1.10
    regs[21] = 192
    regs[22] = 168
    regs[23] = 1
    regs[24] = 10
    regs[45] = 1          # modem_registration = REGISTERED
    regs[46] = 4          # modem_signal_quality = GOOD
    regs[47] = 0          # num_non_critical_error
    regs[48] = 0          # num_status_ef
    regs[49] = 1          # num_status_a
    regs[50] = 1          # num_status_bcd
    regs[51] = 1          # num_charging
    # group_active_power: 11000 W = 11_000_000 mW
    mw = 11_000_000
    regs[52] = (mw >> 16) & 0xFFFF
    regs[53] = mw & 0xFFFF
    # group_current_l1: 16 A = 16_000 mA
    ma = 16_000
    regs[58] = (ma >> 16) & 0xFFFF
    regs[59] = ma & 0xFFFF
    # group_current_l2: unknown (-1)
    regs[60] = 0xFFFF
    regs[61] = 0xFFFF
    regs[64] = 1          # availability = True
    regs[67] = 16         # dynamic_max_current = 16 A
    return regs


def _cp_cfg_regs() -> list[int]:
    """24 registers (x100–x123)."""
    regs = [0] * 24
    regs[0] = 0    # interface_config = socket
    regs[1] = 32   # max_current_cfg = 32 A
    regs[2] = 6    # min_current_cfg = 6 A
    regs[20] = 5   # release_mode = MODBUS
    return regs


def _cp_status_regs() -> list[int]:
    """77 registers (x232–x308)."""
    regs = [0] * 77
    # voltage L1: 230 V = 230_000 mV = 0x00038270
    mv = 230_000
    regs[0] = (mv >> 16) & 0xFFFF
    regs[1] = mv & 0xFFFF
    # current L1: 16 A = 16_000 mA
    ma = 16_000
    regs[6] = (ma >> 16) & 0xFFFF
    regs[7] = ma & 0xFFFF
    # current L2/L3: unknown sentinel
    regs[8] = 0xFFFF; regs[9] = 0xFFFF
    regs[10] = 0xFFFF; regs[11] = 0xFFFF
    # active_power: 3680 W = 3_680_000 mW
    mw = 3_680_000
    regs[12] = (mw >> 16) & 0xFFFF
    regs[13] = mw & 0xFFFF
    # energy_active: 123456 Wh (4 words)
    wh = 123_456
    regs[18] = 0; regs[19] = 0
    regs[20] = (wh >> 16) & 0xFFFF
    regs[21] = wh & 0xFFFF
    # session_energy: 5000 Wh (4 words)
    swh = 5_000
    regs[57] = 0; regs[58] = 0
    regs[59] = (swh >> 16) & 0xFFFF
    regs[60] = swh & 0xFFFF
    # vehicle_status: C2 = 0x4332
    regs[67] = 0x4332
    # control registers (offset 68+)
    regs[68] = 1   # charging_release = True
    regs[69] = 16  # max_current = 16 A
    regs[72] = 1   # available = True
    regs[74] = 16  # watchdog_current = 16 A
    regs[75] = 65535  # watchdog_timer = disabled
    return regs


def _make_response(registers: list[int]) -> MagicMock:
    r = MagicMock()
    r.isError.return_value = False
    r.registers = registers
    return r


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_pymodbus():
    with patch("aiophoenixcontactcharx.client.AsyncModbusTcpClient") as cls:
        instance = cls.return_value
        instance.connect = AsyncMock(return_value=True)
        instance.connected = True
        instance.close = MagicMock()
        yield instance


# ---------------------------------------------------------------------------
# Connection tests
# ---------------------------------------------------------------------------

class TestConnection:
    async def test_connect_success(self, mock_pymodbus):
        client = CharxClient("192.168.1.1")
        await client.connect()
        mock_pymodbus.connect.assert_awaited_once()

    async def test_connect_returns_false_raises(self, mock_pymodbus):
        mock_pymodbus.connect.return_value = False
        client = CharxClient("192.168.1.1")
        with pytest.raises(CharxConnectionError, match="Cannot connect"):
            await client.connect()

    async def test_connect_exception_raises(self, mock_pymodbus):
        mock_pymodbus.connect.side_effect = OSError("refused")
        client = CharxClient("192.168.1.1")
        with pytest.raises(CharxConnectionError):
            await client.connect()

    async def test_context_manager_closes(self, mock_pymodbus):
        async with CharxClient("192.168.1.1"):
            pass
        mock_pymodbus.close.assert_called_once()

    async def test_reconnects_when_disconnected(self, mock_pymodbus):
        mock_pymodbus.connected = False
        mock_pymodbus.read_holding_registers = AsyncMock(
            return_value=_make_response([0] * 68)
        )
        client = CharxClient("192.168.1.1")
        # Should reconnect transparently
        await client._read(100, 68)
        assert mock_pymodbus.connect.await_count == 1


# ---------------------------------------------------------------------------
# get_device_info
# ---------------------------------------------------------------------------

class TestGetDeviceInfo:
    async def test_parses_all_fields(self, mock_pymodbus):
        mock_pymodbus.read_holding_registers = AsyncMock(
            return_value=_make_response(_global_regs())
        )
        async with CharxClient("192.168.1.1") as client:
            info = await client.get_device_info()

        assert info.designation == "CHARX TEST"
        assert info.software_version == "1.9.0"
        assert info.num_controllers == 2
        assert info.mac_eth0 == "AA:BB:CC:DD:EE:FF"
        assert info.ip_eth0 == "192.168.1.10"
        assert info.num_charging == 1
        assert info.group_active_power_w == pytest.approx(11000.0, rel=1e-3)
        assert info.group_current_l1_a == pytest.approx(16.0, rel=1e-3)
        assert info.group_current_l2_a is None   # unknown sentinel
        assert info.dynamic_max_current_a == 16
        assert info.availability is True

    async def test_unrecognised_modem_registration_logs_warning(self, mock_pymodbus, caplog):
        regs = _global_regs()
        regs[45] = 99  # not a valid ModemRegistration value
        mock_pymodbus.read_holding_registers = AsyncMock(
            return_value=_make_response(regs)
        )
        with caplog.at_level(logging.WARNING, logger="aiophoenixcontactcharx.client"):
            async with CharxClient("192.168.1.1") as client:
                info = await client.get_device_info()

        assert info.modem_registration == ModemRegistration.UNKNOWN
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "WARNING"
        assert "99" in caplog.records[0].message

    async def test_unrecognised_modem_signal_quality_logs_warning(self, mock_pymodbus, caplog):
        regs = _global_regs()
        regs[46] = 99  # not a valid ModemSignalQuality value
        mock_pymodbus.read_holding_registers = AsyncMock(
            return_value=_make_response(regs)
        )
        with caplog.at_level(logging.WARNING, logger="aiophoenixcontactcharx.client"):
            async with CharxClient("192.168.1.1") as client:
                info = await client.get_device_info()

        assert info.modem_signal_quality == ModemSignalQuality.UNKNOWN
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "WARNING"
        assert "99" in caplog.records[0].message

    async def test_modbus_error_raises(self, mock_pymodbus):
        err_resp = MagicMock()
        err_resp.isError.return_value = True
        mock_pymodbus.read_holding_registers = AsyncMock(return_value=err_resp)
        async with CharxClient("192.168.1.1") as client:
            with pytest.raises(CharxModbusError):
                await client.get_device_info()


# ---------------------------------------------------------------------------
# get_charging_point_config
# ---------------------------------------------------------------------------

class TestGetChargingPointConfig:
    async def test_parses_proximity_cfg_default(self, mock_pymodbus):
        regs = _cp_cfg_regs()
        regs[10] = 0   # IEC 61851-1 standard
        mock_pymodbus.read_holding_registers = AsyncMock(
            return_value=_make_response(regs)
        )
        async with CharxClient("192.168.1.1") as client:
            config = await client.get_charging_point_config(1)

        assert config.proximity_cfg == 0

    async def test_parses_proximity_cfg_nonzero(self, mock_pymodbus):
        regs = _cp_cfg_regs()
        regs[10] = 3   # non-standard / future mode
        mock_pymodbus.read_holding_registers = AsyncMock(
            return_value=_make_response(regs)
        )
        async with CharxClient("192.168.1.1") as client:
            config = await client.get_charging_point_config(1)

        assert config.proximity_cfg == 3

    async def test_parses_overcurrent_monitoring_off(self, mock_pymodbus):
        regs = _cp_cfg_regs()
        regs[11] = 0   # OFF
        mock_pymodbus.read_holding_registers = AsyncMock(
            return_value=_make_response(regs)
        )
        from aiophoenixcontactcharx.models import OvercurrentMonitoring
        async with CharxClient("192.168.1.1") as client:
            config = await client.get_charging_point_config(1)

        assert config.overcurrent_monitoring == OvercurrentMonitoring.OFF

    async def test_parses_overcurrent_monitoring_pct120(self, mock_pymodbus):
        regs = _cp_cfg_regs()
        regs[11] = 1   # PCT120_10S
        mock_pymodbus.read_holding_registers = AsyncMock(
            return_value=_make_response(regs)
        )
        from aiophoenixcontactcharx.models import OvercurrentMonitoring
        async with CharxClient("192.168.1.1") as client:
            config = await client.get_charging_point_config(1)

        assert config.overcurrent_monitoring == OvercurrentMonitoring.PCT120_10S

    async def test_parses_overcurrent_monitoring_ev_ze_ready(self, mock_pymodbus):
        regs = _cp_cfg_regs()
        regs[11] = 2   # EV_ZE_READY
        mock_pymodbus.read_holding_registers = AsyncMock(
            return_value=_make_response(regs)
        )
        from aiophoenixcontactcharx.models import OvercurrentMonitoring
        async with CharxClient("192.168.1.1") as client:
            config = await client.get_charging_point_config(1)

        assert config.overcurrent_monitoring == OvercurrentMonitoring.EV_ZE_READY

    async def test_unrecognised_overcurrent_falls_back_to_off(self, mock_pymodbus, caplog):
        regs = _cp_cfg_regs()
        regs[11] = 99  # unknown value
        mock_pymodbus.read_holding_registers = AsyncMock(
            return_value=_make_response(regs)
        )
        from aiophoenixcontactcharx.models import OvercurrentMonitoring
        with caplog.at_level(logging.WARNING, logger="aiophoenixcontactcharx.client"):
            async with CharxClient("192.168.1.1") as client:
                config = await client.get_charging_point_config(1)

        assert config.overcurrent_monitoring == OvercurrentMonitoring.OFF
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "WARNING"
        assert "99" in caplog.records[0].message

    async def test_energy_meter_type_unknown_sentinel_decodes_silently(self, mock_pymodbus, caplog):
        regs = _cp_cfg_regs()
        regs[12] = 65535  # EnergyMeterType.UNKNOWN — legitimate device value, no warning
        mock_pymodbus.read_holding_registers = AsyncMock(
            return_value=_make_response(regs)
        )
        with caplog.at_level(logging.WARNING, logger="aiophoenixcontactcharx.client"):
            async with CharxClient("192.168.1.1") as client:
                config = await client.get_charging_point_config(1)

        assert config.energy_meter_type == EnergyMeterType.UNKNOWN
        assert len(caplog.records) == 0   # no warning for a recognised sentinel

    async def test_unrecognised_energy_meter_type_logs_warning(self, mock_pymodbus, caplog):
        regs = _cp_cfg_regs()
        regs[12] = 99  # not a valid EnergyMeterType value
        mock_pymodbus.read_holding_registers = AsyncMock(
            return_value=_make_response(regs)
        )
        with caplog.at_level(logging.WARNING, logger="aiophoenixcontactcharx.client"):
            async with CharxClient("192.168.1.1") as client:
                config = await client.get_charging_point_config(1)

        assert config.energy_meter_type == EnergyMeterType.UNKNOWN
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "WARNING"
        assert "99" in caplog.records[0].message

    async def test_unrecognised_temp_monitoring_logs_warning(self, mock_pymodbus, caplog):
        regs = _cp_cfg_regs()
        regs[8] = 99  # not a valid TempMonitoring value
        mock_pymodbus.read_holding_registers = AsyncMock(
            return_value=_make_response(regs)
        )
        with caplog.at_level(logging.WARNING, logger="aiophoenixcontactcharx.client"):
            async with CharxClient("192.168.1.1") as client:
                config = await client.get_charging_point_config(1)

        assert config.temp_monitoring == TempMonitoring.INACTIVE
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "WARNING"
        assert "99" in caplog.records[0].message

    async def test_unrecognised_release_mode_logs_warning(self, mock_pymodbus, caplog):
        regs = _cp_cfg_regs()
        regs[20] = 99  # not a valid ReleaseMode value
        mock_pymodbus.read_holding_registers = AsyncMock(
            return_value=_make_response(regs)
        )
        with caplog.at_level(logging.WARNING, logger="aiophoenixcontactcharx.client"):
            async with CharxClient("192.168.1.1") as client:
                config = await client.get_charging_point_config(1)

        assert config.release_mode == ReleaseMode.DASHBOARD
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "WARNING"
        assert "99" in caplog.records[0].message


# ---------------------------------------------------------------------------
# get_charging_point_status_and_control
# ---------------------------------------------------------------------------

class TestGetChargingPointStatus:
    async def test_parses_status(self, mock_pymodbus):
        mock_pymodbus.read_holding_registers = AsyncMock(
            return_value=_make_response(_cp_status_regs())
        )
        async with CharxClient("192.168.1.1") as client:
            status, control = await client.get_charging_point_status_and_control(1)

        assert status.vehicle_status == "C2"
        assert status.voltage_l1_v == pytest.approx(230.0, rel=1e-3)
        assert status.current_l1_a == pytest.approx(16.0, rel=1e-3)
        assert status.current_l2_a is None   # sentinel
        assert status.current_l3_a is None
        assert status.active_power_w == pytest.approx(3680.0, rel=1e-3)
        assert status.energy_active_wh == 123_456
        assert status.energy_active_kwh == pytest.approx(123.456, rel=1e-3)
        assert status.session_energy_wh == 5_000

    async def test_parses_control(self, mock_pymodbus):
        mock_pymodbus.read_holding_registers = AsyncMock(
            return_value=_make_response(_cp_status_regs())
        )
        async with CharxClient("192.168.1.1") as client:
            _, control = await client.get_charging_point_status_and_control(1)

        assert control.charging_release is True
        assert control.max_current_a == 16
        assert control.available is True
        assert control.watchdog_timer_s == 65535
        assert control.force_unlock_pending is False

    async def test_force_unlock_pending_true(self, mock_pymodbus):
        regs = _cp_status_regs()
        regs[72] = 0   # available = False — distinguishes regs[72] from regs[73]
        regs[73] = 1   # X305 — force-unlock pending
        mock_pymodbus.read_holding_registers = AsyncMock(
            return_value=_make_response(regs)
        )
        async with CharxClient("192.168.1.1") as client:
            _, control = await client.get_charging_point_status_and_control(1)

        assert control.available is False       # confirms regs[72] was read correctly
        assert control.force_unlock_pending is True

    async def test_active_power_with_msb_set_is_positive(self, mock_pymodbus):
        regs = _cp_status_regs()
        # 0x80000001 = 2_147_483_649 mW unsigned; _s32 would give -2_147_483_647
        regs[12] = 0x8000
        regs[13] = 0x0001
        mock_pymodbus.read_holding_registers = AsyncMock(
            return_value=_make_response(regs)
        )
        async with CharxClient("192.168.1.1") as client:
            status, _ = await client.get_charging_point_status_and_control(1)

        assert status.active_power_w > 0

    async def test_register_address_for_cp2(self, mock_pymodbus):
        """Verify that CP2 reads start at address 2232, not 1232."""
        mock_pymodbus.read_holding_registers = AsyncMock(
            return_value=_make_response(_cp_status_regs())
        )
        async with CharxClient("192.168.1.1") as client:
            await client.get_charging_point_status_and_control(2)

        call_args = mock_pymodbus.read_holding_registers.call_args
        assert call_args.kwargs["address"] == 2232


# ---------------------------------------------------------------------------
# pack_digital_outputs
# ---------------------------------------------------------------------------

class TestPackDigitalOutputs:
    def test_all_floating(self):
        from aiophoenixcontactcharx.models import DigitalOutputMode, pack_digital_outputs
        assert pack_digital_outputs(
            DigitalOutputMode.FLOATING, DigitalOutputMode.FLOATING,
            DigitalOutputMode.FLOATING, DigitalOutputMode.FLOATING,
        ) == 0x0000

    def test_known_combination(self):
        from aiophoenixcontactcharx.models import DigitalOutputMode, pack_digital_outputs
        # HIGH=2 in o1 (bits 3-0), LOW=1 in o2 (bits 7-4), FLOATING=0 in o3, HIGH=2 in o4 (bits 15-12)
        result = pack_digital_outputs(
            DigitalOutputMode.HIGH, DigitalOutputMode.LOW,
            DigitalOutputMode.FLOATING, DigitalOutputMode.HIGH,
        )
        assert result == (2 << 0) | (1 << 4) | (0 << 8) | (2 << 12)

    def test_all_pulsatile(self):
        from aiophoenixcontactcharx.models import DigitalOutputMode, pack_digital_outputs
        result = pack_digital_outputs(
            DigitalOutputMode.PULSATILE, DigitalOutputMode.PULSATILE,
            DigitalOutputMode.PULSATILE, DigitalOutputMode.PULSATILE,
        )
        assert result == 0x4444

    def test_importable_from_package(self):
        from aiophoenixcontactcharx import DigitalOutputMode, pack_digital_outputs
        assert DigitalOutputMode.HIGH == 2
        assert callable(pack_digital_outputs)

    def test_nibble_overflow_clamped(self):
        from aiophoenixcontactcharx.models import pack_digital_outputs
        # Raw int 16 (0x10) would bleed into o2 nibble without the & 0xF mask
        result = pack_digital_outputs(16, 0, 0, 0)  # type: ignore[arg-type]
        assert result & 0x00F0 == 0, "nibble overflow must not bleed into o2"
        assert result & 0x000F == 0, "o1 nibble should be 0 (16 & 0xF == 0)"


# ---------------------------------------------------------------------------
# ErrorCode
# ---------------------------------------------------------------------------

class TestErrorCode:
    async def test_no_errors(self, mock_pymodbus):
        from aiophoenixcontactcharx.models import ErrorCode
        regs = _cp_status_regs()
        regs[61] = 0
        regs[62] = 0
        mock_pymodbus.read_holding_registers = AsyncMock(
            return_value=_make_response(regs)
        )
        async with CharxClient("192.168.1.1") as client:
            status, _ = await client.get_charging_point_status_and_control(1)

        assert status.error_code == ErrorCode(0)
        assert not status.error_code   # falsy when zero

    async def test_single_bit_cp_error(self, mock_pymodbus):
        from aiophoenixcontactcharx.models import ErrorCode
        mask = int(ErrorCode.CP_ERROR)
        regs = _cp_status_regs()
        regs[61] = (mask >> 16) & 0xFFFF
        regs[62] = mask & 0xFFFF
        mock_pymodbus.read_holding_registers = AsyncMock(
            return_value=_make_response(regs)
        )
        async with CharxClient("192.168.1.1") as client:
            status, _ = await client.get_charging_point_status_and_control(1)

        assert ErrorCode.CP_ERROR in status.error_code

    async def test_multi_bit_error(self, mock_pymodbus):
        from aiophoenixcontactcharx.models import ErrorCode
        mask = int(ErrorCode.TEMPERATURE_TOO_HIGH | ErrorCode.OVERCURRENT_DETECTED)
        regs = _cp_status_regs()
        regs[61] = (mask >> 16) & 0xFFFF
        regs[62] = mask & 0xFFFF
        mock_pymodbus.read_holding_registers = AsyncMock(
            return_value=_make_response(regs)
        )
        async with CharxClient("192.168.1.1") as client:
            status, _ = await client.get_charging_point_status_and_control(1)

        assert ErrorCode.TEMPERATURE_TOO_HIGH in status.error_code
        assert ErrorCode.OVERCURRENT_DETECTED in status.error_code
        assert ErrorCode.CP_ERROR not in status.error_code

    async def test_high_bits_residual_current(self, mock_pymodbus):
        from aiophoenixcontactcharx.models import ErrorCode
        # Exercises bits 30 and 31 — the MSB pair that could be silently swapped
        mask = int(ErrorCode.RESIDUAL_CURRENT_TRIP | ErrorCode.RESIDUAL_CURRENT_SENSOR_ERROR)
        regs = _cp_status_regs()
        regs[61] = (mask >> 16) & 0xFFFF
        regs[62] = mask & 0xFFFF
        mock_pymodbus.read_holding_registers = AsyncMock(
            return_value=_make_response(regs)
        )
        async with CharxClient("192.168.1.1") as client:
            status, _ = await client.get_charging_point_status_and_control(1)

        assert ErrorCode.RESIDUAL_CURRENT_TRIP in status.error_code
        assert ErrorCode.RESIDUAL_CURRENT_SENSOR_ERROR in status.error_code
        assert ErrorCode.CONTACTOR_ERROR not in status.error_code

    async def test_reserved_bit_logs_warning(self, mock_pymodbus):
        from aiophoenixcontactcharx.models import ErrorCode
        # Bit 8 is in the reserved range (bits 7–15); named bits still decode correctly.
        mask = int(ErrorCode.CP_ERROR) | (1 << 8)
        regs = _cp_status_regs()
        regs[61] = (mask >> 16) & 0xFFFF
        regs[62] = mask & 0xFFFF
        mock_pymodbus.read_holding_registers = AsyncMock(
            return_value=_make_response(regs)
        )
        with patch("aiophoenixcontactcharx.client._LOGGER") as mock_logger:
            async with CharxClient("192.168.1.1") as client:
                status, _ = await client.get_charging_point_status_and_control(1)

        mock_logger.warning.assert_called_once()
        # First format arg is the unknown-bits mask; second is the raw value
        assert mock_logger.warning.call_args.args[1] == (1 << 8)
        assert ErrorCode.CP_ERROR in status.error_code


# ---------------------------------------------------------------------------
# fetch_data
# ---------------------------------------------------------------------------

class TestFetchData:
    async def test_num_charging_points_above_max_raises(self, mock_pymodbus):
        async with CharxClient("192.168.1.1") as client:
            with pytest.raises(ValueError, match="1–12"):
                await client.fetch_data(num_charging_points=13)

    async def test_num_charging_points_zero_raises(self, mock_pymodbus):
        async with CharxClient("192.168.1.1") as client:
            with pytest.raises(ValueError, match="1–12"):
                await client.fetch_data(num_charging_points=0)

    async def test_request_count(self, mock_pymodbus):
        """1 global + 2 per CP (config + status) = 3 requests for 1 CP."""
        mock_pymodbus.read_holding_registers = AsyncMock(side_effect=[
            _make_response(_global_regs()),
            _make_response(_cp_cfg_regs()),
            _make_response(_cp_status_regs()),
        ])
        async with CharxClient("192.168.1.1") as client:
            data = await client.fetch_data(1)

        assert mock_pymodbus.read_holding_registers.await_count == 3
        assert len(data.charging_points) == 1

    async def test_two_charging_points(self, mock_pymodbus):
        """1 global + 4 CP reads = 5 requests for 2 CPs."""
        mock_pymodbus.read_holding_registers = AsyncMock(side_effect=[
            _make_response(_global_regs()),
            _make_response(_cp_cfg_regs()),
            _make_response(_cp_status_regs()),
            _make_response(_cp_cfg_regs()),
            _make_response(_cp_status_regs()),
        ])
        async with CharxClient("192.168.1.1") as client:
            data = await client.fetch_data(2)

        assert len(data.charging_points) == 2
        assert data.charging_points[0].charging_point == 1
        assert data.charging_points[1].charging_point == 2

    async def test_derived_properties(self, mock_pymodbus):
        mock_pymodbus.read_holding_registers = AsyncMock(side_effect=[
            _make_response(_global_regs()),
            _make_response(_cp_cfg_regs()),
            _make_response(_cp_status_regs()),
        ])
        async with CharxClient("192.168.1.1") as client:
            data = await client.fetch_data(1)

        cp = data.charging_points[0]
        assert cp.is_charging is True       # C2
        assert cp.is_connected is True
        assert cp.has_error is False
        assert cp.is_unavailable is False

    async def test_f0_is_unavailable_not_error(self, mock_pymodbus):
        regs = _cp_status_regs()
        regs[67] = 0x4630  # F0
        mock_pymodbus.read_holding_registers = AsyncMock(side_effect=[
            _make_response(_global_regs()),
            _make_response(_cp_cfg_regs()),
            _make_response(regs),
        ])
        async with CharxClient("192.168.1.1") as client:
            data = await client.fetch_data(1)

        cp = data.charging_points[0]
        assert cp.is_unavailable is True
        assert cp.has_error is False

    async def test_e0_is_error_not_unavailable(self, mock_pymodbus):
        regs = _cp_status_regs()
        regs[67] = 0x4530  # E0
        mock_pymodbus.read_holding_registers = AsyncMock(side_effect=[
            _make_response(_global_regs()),
            _make_response(_cp_cfg_regs()),
            _make_response(regs),
        ])
        async with CharxClient("192.168.1.1") as client:
            data = await client.fetch_data(1)

        cp = data.charging_points[0]
        assert cp.has_error is True
        assert cp.is_unavailable is False

    async def test_d2_is_charging(self, mock_pymodbus):
        regs = _cp_status_regs()
        regs[67] = 0x4432  # D2
        mock_pymodbus.read_holding_registers = AsyncMock(side_effect=[
            _make_response(_global_regs()),
            _make_response(_cp_cfg_regs()),
            _make_response(regs),
        ])
        async with CharxClient("192.168.1.1") as client:
            data = await client.fetch_data(1)

        cp = data.charging_points[0]
        assert cp.is_charging is True
        assert cp.is_connected is True

    async def test_d1_is_not_charging(self, mock_pymodbus):
        regs = _cp_status_regs()
        regs[67] = 0x4431  # D1
        mock_pymodbus.read_holding_registers = AsyncMock(side_effect=[
            _make_response(_global_regs()),
            _make_response(_cp_cfg_regs()),
            _make_response(regs),
        ])
        async with CharxClient("192.168.1.1") as client:
            data = await client.fetch_data(1)

        cp = data.charging_points[0]
        assert cp.is_charging is False
        assert cp.is_connected is True


# ---------------------------------------------------------------------------
# Control writes
# ---------------------------------------------------------------------------

class TestControlWrites:
    async def test_set_charging_release_on(self, mock_pymodbus):
        mock_pymodbus.write_register = AsyncMock(
            return_value=MagicMock(isError=lambda: False)
        )
        async with CharxClient("192.168.1.1") as client:
            await client.set_charging_release(1, True)

        mock_pymodbus.write_register.assert_awaited_once_with(
            address=1300, value=1, device_id=1
        )

    async def test_set_charging_release_off(self, mock_pymodbus):
        mock_pymodbus.write_register = AsyncMock(
            return_value=MagicMock(isError=lambda: False)
        )
        async with CharxClient("192.168.1.1") as client:
            await client.set_charging_release(1, False)

        mock_pymodbus.write_register.assert_awaited_once_with(
            address=1300, value=0, device_id=1
        )

    async def test_set_max_current_valid(self, mock_pymodbus):
        mock_pymodbus.write_register = AsyncMock(
            return_value=MagicMock(isError=lambda: False)
        )
        async with CharxClient("192.168.1.1") as client:
            await client.set_max_current(1, 11)

        mock_pymodbus.write_register.assert_awaited_once_with(
            address=1301, value=11, device_id=1
        )

    async def test_set_max_current_below_minimum_raises(self, mock_pymodbus):
        async with CharxClient("192.168.1.1") as client:
            with pytest.raises(ValueError, match="6–80"):
                await client.set_max_current(1, 5)

    async def test_set_max_current_above_maximum_raises(self, mock_pymodbus):
        async with CharxClient("192.168.1.1") as client:
            with pytest.raises(ValueError, match="6–80"):
                await client.set_max_current(1, 81)

    async def test_set_availability(self, mock_pymodbus):
        mock_pymodbus.write_register = AsyncMock(
            return_value=MagicMock(isError=lambda: False)
        )
        async with CharxClient("192.168.1.1") as client:
            await client.set_availability(2, False)

        mock_pymodbus.write_register.assert_awaited_once_with(
            address=2304, value=0, device_id=1
        )

    async def test_set_locking_locked(self, mock_pymodbus):
        mock_pymodbus.write_register = AsyncMock(
            return_value=MagicMock(isError=lambda: False)
        )
        async with CharxClient("192.168.1.1") as client:
            await client.set_locking(1, True)

        mock_pymodbus.write_register.assert_awaited_once_with(
            address=1303, value=1, device_id=1
        )

    async def test_set_locking_unlocked(self, mock_pymodbus):
        mock_pymodbus.write_register = AsyncMock(
            return_value=MagicMock(isError=lambda: False)
        )
        async with CharxClient("192.168.1.1") as client:
            await client.set_locking(2, False)

        mock_pymodbus.write_register.assert_awaited_once_with(
            address=2303, value=0, device_id=1
        )

    async def test_set_locking_invalid_charging_point_raises(self, mock_pymodbus):
        async with CharxClient("192.168.1.1") as client:
            with pytest.raises(ValueError, match="1.12"):
                await client.set_locking(13, True)

    async def test_set_locking_charging_point_zero_raises(self, mock_pymodbus):
        async with CharxClient("192.168.1.1") as client:
            with pytest.raises(ValueError, match="1.12"):
                await client.set_locking(0, True)

    async def test_set_digital_outputs_writes_packed_value(self, mock_pymodbus):
        from aiophoenixcontactcharx.models import DigitalOutputMode, pack_digital_outputs
        mock_pymodbus.write_register = AsyncMock(
            return_value=MagicMock(isError=lambda: False)
        )
        value = pack_digital_outputs(
            DigitalOutputMode.HIGH, DigitalOutputMode.LOW,
            DigitalOutputMode.FLOATING, DigitalOutputMode.HIGH,
        )
        async with CharxClient("192.168.1.1") as client:
            await client.set_digital_outputs(1, value)

        mock_pymodbus.write_register.assert_awaited_once_with(
            address=1302, value=value, device_id=1
        )

    async def test_set_digital_outputs_invalid_charging_point_raises(self, mock_pymodbus):
        async with CharxClient("192.168.1.1") as client:
            with pytest.raises(ValueError, match="1.12"):
                await client.set_digital_outputs(0, 0)

    async def test_set_digital_outputs_value_overflow_raises(self, mock_pymodbus):
        async with CharxClient("192.168.1.1") as client:
            with pytest.raises(ValueError, match="0xFFFF"):
                await client.set_digital_outputs(1, 0x10000)

    async def test_set_group_availability_false(self, mock_pymodbus):
        mock_pymodbus.write_register = AsyncMock(
            return_value=MagicMock(isError=lambda: False)
        )
        async with CharxClient("192.168.1.1") as client:
            await client.set_group_availability(False)

        mock_pymodbus.write_register.assert_awaited_once_with(
            address=164, value=0, device_id=1
        )

    async def test_set_group_availability_true(self, mock_pymodbus):
        mock_pymodbus.write_register = AsyncMock(
            return_value=MagicMock(isError=lambda: False)
        )
        async with CharxClient("192.168.1.1") as client:
            await client.set_group_availability(True)

        mock_pymodbus.write_register.assert_awaited_once_with(
            address=164, value=1, device_id=1
        )

    async def test_set_dynamic_max_current(self, mock_pymodbus):
        mock_pymodbus.write_register = AsyncMock(
            return_value=MagicMock(isError=lambda: False)
        )
        async with CharxClient("192.168.1.1") as client:
            await client.set_dynamic_max_current(32)

        mock_pymodbus.write_register.assert_awaited_once_with(
            address=167, value=32, device_id=1
        )

    async def test_set_watchdog_below_minimum_raises(self, mock_pymodbus):
        async with CharxClient("192.168.1.1") as client:
            with pytest.raises(ValueError, match="6–80"):
                await client.set_watchdog(1, timer_s=60, fallback_current_a=5)

    async def test_set_watchdog_above_maximum_raises(self, mock_pymodbus):
        async with CharxClient("192.168.1.1") as client:
            with pytest.raises(ValueError, match="6–80"):
                await client.set_watchdog(1, timer_s=60, fallback_current_a=81)

    async def test_set_watchdog_boundary_values_accepted(self, mock_pymodbus):
        mock_pymodbus.write_register = AsyncMock(
            return_value=MagicMock(isError=lambda: False)
        )
        async with CharxClient("192.168.1.1") as client:
            await client.set_watchdog(1, timer_s=60, fallback_current_a=6)
            await client.set_watchdog(1, timer_s=60, fallback_current_a=80)

    async def test_set_watchdog_disable_with_zero_current_accepted(self, mock_pymodbus):
        mock_pymodbus.write_register = AsyncMock(
            return_value=MagicMock(isError=lambda: False)
        )
        async with CharxClient("192.168.1.1") as client:
            # timer_s=65535 disables the watchdog; fallback_current_a is irrelevant
            await client.set_watchdog(1, timer_s=65535, fallback_current_a=0)

    async def test_write_modbus_error_raises(self, mock_pymodbus):
        err_resp = MagicMock()
        err_resp.isError.return_value = True
        mock_pymodbus.write_register = AsyncMock(return_value=err_resp)
        async with CharxClient("192.168.1.1") as client:
            with pytest.raises(CharxModbusError):
                await client.set_charging_release(1, True)
