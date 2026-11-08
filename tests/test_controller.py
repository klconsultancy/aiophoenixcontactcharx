from ipaddress import IPv4Address
from typing import assert_type

import pytest
from modbus_connection.exceptions import (
    IllegalDataAddressError,
    ModbusConnectionError,
    ModbusTimeoutError,
)
from modbus_connection.mock import MockModbusUnit

from aiophoenixcontactcharx import (
    MAX_CHARGING_POINTS,
    ChargingInterface,
    CharxController,
    EnergyMeterType,
    ErrorCode,
    ModemRegistration,
    ReleaseMode,
    TempMonitoring,
    VehicleStatus,
    charging_point_name,
)
from tests.conftest import SYNTHETIC

# The documented ranges the reads must stay in (tests/test_register_map.py checks these
# against the manual).
GLOBAL_RANGES = ((100, 146), (147, 164), (167, 167))
POINT_RANGES = ((100, 123), (232, 307))


async def updated(unit: MockModbusUnit) -> CharxController:
    controller = CharxController(unit)
    report = await controller.async_update()
    assert report.complete
    return controller


# -- placing the Charging Points ----------------------------------------------------


async def test_no_charging_points_before_the_first_update(controller_unit: MockModbusUnit) -> None:
    controller = CharxController(controller_unit)

    assert controller.charging_points == ()
    assert controller.names == ("device_info", "group")
    assert controller_unit.read_events == []


async def test_places_a_charging_point_per_charging_controller(
    controller_unit: MockModbusUnit,
) -> None:
    controller = await updated(controller_unit)

    assert [cp.number for cp in controller.charging_points] == [1, 2]
    assert controller.names == ("device_info", "group", "charging_point_1", "charging_point_2")


async def test_caps_the_charging_points_at_twelve(
    controller_unit: MockModbusUnit, caplog: pytest.LogCaptureFixture
) -> None:
    controller_unit.holding[114] = 13

    controller = await updated(controller_unit)

    assert len(controller.charging_points) == MAX_CHARGING_POINTS
    assert "reports 13 Charging Controllers; reading the first 12" in caplog.text


async def test_no_charging_controllers_places_none(
    controller_unit: MockModbusUnit, caplog: pytest.LogCaptureFixture
) -> None:
    controller_unit.holding[114] = 0

    controller = await updated(controller_unit)

    assert controller.charging_points == ()
    assert "reports no Charging Controllers" in caplog.text


async def test_places_the_charging_points_once(controller_unit: MockModbusUnit) -> None:
    controller = await updated(controller_unit)
    controller_unit.holding[114] = 3

    await controller.async_update()

    assert len(controller.charging_points) == 2


# -- decoding ----------------------------------------------------------------------


async def test_decodes_the_controller_info(controller_unit: MockModbusUnit) -> None:
    info = (await updated(controller_unit)).device_info

    assert info.designation == "CHARX SEC-3100"
    assert info.software_version == "1.7.3"
    assert info.charging_controllers == 2
    assert info.mac_eth0 == "a8:74:1d:00:12:ab"
    assert info.ip_eth0 == IPv4Address("192.168.1.50")
    assert info.subnet_mask_eth0 == IPv4Address("255.255.255.0")
    assert info.gateway_eth0 == IPv4Address(0)  # a placeholder: reads 0.0.0.0
    assert info.modem_registration is ModemRegistration.UNKNOWN


async def test_decodes_the_group(controller_unit: MockModbusUnit) -> None:
    group = (await updated(controller_unit)).group

    assert group.charging == 1
    assert group.status_a == 1
    assert group.active_power == pytest.approx(7398.0)
    assert group.reactive_power == pytest.approx(-120.0)
    assert group.apparent_power == pytest.approx(7401.0)
    assert group.available is True
    assert group.dynamic_max_current == 32


async def test_a_total_current_of_minus_one_is_none(controller_unit: MockModbusUnit) -> None:
    # -1: the phase rotation of a configured Charging Point is unknown.
    group = (await updated(controller_unit)).group

    assert (group.current_l1, group.current_l2, group.current_l3) == (None, None, None)


async def test_decodes_a_charging_point(controller_unit: MockModbusUnit) -> None:
    cp = (await updated(controller_unit)).charging_points[0]

    assert cp.interface is ChargingInterface.SOCKET
    assert cp.max_current_config == 32
    assert cp.rcm_configured is True
    assert cp.temperature_monitoring is TempMonitoring.PT1000
    assert cp.energy_meter_type is EnergyMeterType.EEM_EM357
    assert cp.release_mode is ReleaseMode.MODBUS
    assert cp.uid == "CP0001"
    assert cp.voltage_l1 == pytest.approx(230.1)
    assert cp.current_l1 == pytest.approx(10.7)
    assert cp.active_power == pytest.approx(7398.0)
    assert cp.reactive_power == pytest.approx(-40.0)
    assert cp.active_energy == pytest.approx(10450.504)
    assert cp.reactive_energy == pytest.approx(-1.25)
    assert cp.session_energy == pytest.approx(3.212)
    assert cp.rfid_uid == "04A2B3C4D5"
    assert cp.connection_time == 1830
    assert cp.charging_duration == 1604
    assert cp.charging_current == 16
    assert cp.vehicle_status is VehicleStatus.C2
    assert cp.charging_release is True
    assert cp.max_current == 16
    assert cp.digital_outputs == 0x1123
    assert cp.watchdog_timer == 60


async def test_each_charging_point_reads_its_own_block(controller_unit: MockModbusUnit) -> None:
    first, second = (await updated(controller_unit)).charging_points

    assert first.vehicle_status is VehicleStatus.C2
    assert second.vehicle_status is VehicleStatus.A1
    assert second.current_l1 is None  # -1: phase rotation unknown
    assert second.error_code == ErrorCode.RFID_READER_ERROR
    assert second.active_energy == pytest.approx(812.0)


async def test_a_lifetime_energy_of_zero_is_none(controller_unit: MockModbusUnit) -> None:
    # A meter that is starting reports 0 (haphoenixcontactcharx#38).
    for address in range(1250, 1254):
        controller_unit.holding[address] = 0

    cp = (await updated(controller_unit)).charging_points[0]

    assert cp.active_energy is None


async def test_a_session_energy_of_zero_stays_zero(controller_unit: MockModbusUnit) -> None:
    cp = (await updated(controller_unit)).charging_points[1]

    assert cp.session_energy == 0


@pytest.mark.parametrize(
    ("status", "connected", "charging", "error", "unavailable"),
    [
        (VehicleStatus.A1, False, False, False, False),
        (VehicleStatus.B2, True, False, False, False),
        (VehicleStatus.C2, True, True, False, False),
        (VehicleStatus.D2, True, True, False, False),
        (VehicleStatus.E0, True, False, True, False),
        (VehicleStatus.F0, True, False, False, True),
        (VehicleStatus.IN, False, False, False, False),
    ],
)
async def test_derives_the_charging_state(  # noqa: PLR0913
    controller_unit: MockModbusUnit,
    status: VehicleStatus,
    *,
    connected: bool,
    charging: bool,
    error: bool,
    unavailable: bool,
) -> None:
    controller_unit.holding[1299] = int.from_bytes(status.value.encode(), "big")

    cp = (await updated(controller_unit)).charging_points[0]

    assert (cp.is_connected, cp.is_charging, cp.has_error, cp.is_unavailable) == (
        connected,
        charging,
        error,
        unavailable,
    )


async def test_an_unread_charging_point_is_not_connected(
    controller_unit: MockModbusUnit,
) -> None:
    controller = await updated(controller_unit)
    cp = type(controller.charging_points[0])(controller_unit, 3, base_offset=3000)

    assert cp.vehicle_status is None
    assert cp.is_connected is False
    assert cp.watchdog_enabled is None


async def test_a_watchdog_timer_of_65535_disables_the_watchdog(
    controller_unit: MockModbusUnit,
) -> None:
    first, second = (await updated(controller_unit)).charging_points

    assert first.watchdog_enabled is True
    assert second.watchdog_timer == 65535
    assert second.watchdog_enabled is False


async def test_fields_are_typed(controller_unit: MockModbusUnit) -> None:
    controller = await updated(controller_unit)
    cp = controller.charging_points[0]

    assert_type(cp.active_energy, float | None)
    assert_type(cp.connection_time, int | None)
    assert_type(cp.vehicle_status, VehicleStatus | None)
    assert_type(cp.release_mode, ReleaseMode | None)
    assert_type(cp.error_code, ErrorCode | None)
    assert_type(controller.device_info.ip_eth0, IPv4Address | None)
    assert_type(controller.device_info.mac_eth0, str | None)


# -- reads -------------------------------------------------------------------------


def _within(address: int, count: int, ranges: tuple[tuple[int, int], ...]) -> bool:
    return any(start <= address and address + count - 1 <= end for start, end in ranges)


async def test_reads_stay_in_the_documented_ranges(controller_unit: MockModbusUnit) -> None:
    controller = await updated(controller_unit)
    controller_unit.read_events.clear()

    await controller.async_update()

    for event in controller_unit.read_events:
        block, offset = divmod(event.address, 1000)
        ranges = POINT_RANGES if block else GLOBAL_RANGES
        assert _within(offset, event.count, ranges), (event.address, event.count)


async def test_an_update_takes_one_read_per_documented_range(
    controller_unit: MockModbusUnit,
) -> None:
    controller = await updated(controller_unit)
    controller_unit.read_events.clear()

    await controller.async_update()

    # 3 global ranges and 2 per Charging Point.
    assert len(controller_unit.read_events) == 3 + 2 * 2


async def test_never_reads_the_command_registers(controller_unit: MockModbusUnit) -> None:
    controller = await updated(controller_unit)

    await controller.async_update()

    read = {
        event.address + offset
        for event in controller_unit.read_events
        for offset in range(event.count)
    }
    assert read.isdisjoint({165, 166, 1308, 2308})


# -- failures ----------------------------------------------------------------------


async def test_a_failing_charging_point_fails_alone(controller_unit: MockModbusUnit) -> None:
    controller = await updated(controller_unit)
    controller_unit.holding[1297] = 10
    controller_unit.fail_read(2232, IllegalDataAddressError(3))

    report = await controller.async_update()

    assert report.updated == {"device_info", "group", charging_point_name(1)}
    assert set(report.failed) == {charging_point_name(2)}
    assert controller.charging_points[0].charging_current == 10
    # The failed Charging Point keeps the values of the last read.
    assert controller.charging_points[1].vehicle_status is VehicleStatus.A1


async def test_a_lost_connection_raises(controller_unit: MockModbusUnit) -> None:
    controller = await updated(controller_unit)
    controller_unit.fail_requests(ModbusConnectionError("gone"))

    with pytest.raises(ModbusConnectionError):
        await controller.async_update()


async def test_a_timeout_before_any_answer_raises(controller_unit: MockModbusUnit) -> None:
    controller = await updated(controller_unit)
    controller_unit.fail_requests(ModbusTimeoutError("silent"))

    with pytest.raises(ModbusTimeoutError):
        await controller.async_update()


async def test_a_failed_setup_is_retried(controller_unit: MockModbusUnit) -> None:
    controller = CharxController(controller_unit)
    controller_unit.fail_requests(ModbusConnectionError("gone"))
    with pytest.raises(ModbusConnectionError):
        await controller.async_update()
    controller_unit.fail_requests(None)

    report = await controller.async_update()

    assert report.complete
    assert len(controller.charging_points) == SYNTHETIC["registers"]["holding"]["114"]


async def test_a_refused_identity_register_fails_only_the_device_info(
    controller_unit: MockModbusUnit,
) -> None:
    controller_unit.fail_read(145, IllegalDataAddressError(3))
    controller = CharxController(controller_unit)

    report = await controller.async_update()

    assert set(report.failed) == {"device_info"}
    assert report.updated == {"group", charging_point_name(1), charging_point_name(2)}


async def test_the_setup_reads_only_the_count(controller_unit: MockModbusUnit) -> None:
    controller = CharxController(controller_unit)

    await controller.async_ensure_setup()

    assert [(event.address, event.count) for event in controller_unit.read_events] == [(114, 1)]
