"""Decode the dump of a real controller (tests/fixtures/sec3xxx-1.7.3.json).

Firmware 1.7.3, one Charging Point in OCPP release mode, no vehicle connected. The
dump is anonymized; docs/errata.md records what it showed about the manual.
"""

from ipaddress import IPv4Address

import pytest
from modbus_connection.mock import MockModbusUnit

from aiophoenixcontactcharx import (
    ChargingInterface,
    CharxController,
    DigitalOutputState,
    EnergyMeterType,
    ErrorCode,
    ModemRegistration,
    OvercurrentMonitoring,
    ReleaseMode,
    TempMonitoring,
    VehicleStatus,
)
from tests.conftest import REAL


async def updated(unit: MockModbusUnit) -> CharxController:
    controller = CharxController(unit)
    report = await controller.async_update()
    assert report.complete
    return controller


async def test_one_charging_point(real_unit: MockModbusUnit) -> None:
    controller = await updated(real_unit)

    assert controller.device_info.charging_controllers == 1
    assert [cp.number for cp in controller.charging_points] == [1]


async def test_decodes_the_controller_info(real_unit: MockModbusUnit) -> None:
    info = (await updated(real_unit)).device_info

    # The name set for the controller, not its model (docs/errata.md).
    assert info.designation == "ev3000"
    assert info.software_version == "1.7.3"
    assert info.mac_eth0 == "a8:74:1d:00:00:01"
    assert info.ip_eth0 == IPv4Address("192.0.2.15")
    assert info.ip_eth1 == IPv4Address("192.168.4.1")
    assert info.subnet_mask_eth0 == IPv4Address("255.255.255.0")
    assert info.modem_registration is ModemRegistration.NOT_REGISTERED


async def test_decodes_the_group(real_unit: MockModbusUnit) -> None:
    group = (await updated(real_unit)).group

    assert (group.status_a, group.status_b_c_or_d, group.charging) == (1, 0, 0)
    assert group.active_power == 0
    # A known phase rotation: the totals are 0, not -1.
    assert (group.current_l1, group.current_l2, group.current_l3) == (0, 0, 0)
    assert group.available is True
    # 65535: no dynamic limit set.
    assert group.dynamic_max_current is None


async def test_decodes_the_configuration(real_unit: MockModbusUnit) -> None:
    cp = (await updated(real_unit)).charging_points[0]

    assert cp.interface is ChargingInterface.CONNECTOR
    assert (cp.min_current_config, cp.max_current_config) == (6, 16)
    assert cp.rcm_configured is True
    assert cp.temperature_monitoring is TempMonitoring.INACTIVE
    assert cp.overcurrent_monitoring is OvercurrentMonitoring.OFF
    assert cp.energy_meter_type is EnergyMeterType.EEM_EM357_EE
    assert cp.release_mode is ReleaseMode.OCPP
    assert cp.bus_position == 1
    assert cp.uid == "0a1b2c"
    # The manual's placeholder repeats the controller's UID (docs/errata.md).
    assert cp.rfid_reader_uid == cp.uid


async def test_decodes_the_status(real_unit: MockModbusUnit) -> None:
    cp = (await updated(real_unit)).charging_points[0]

    assert cp.voltage_l1 == pytest.approx(223.579)
    assert cp.voltage_l2 == pytest.approx(227.383)
    assert cp.voltage_l3 == pytest.approx(224.553)
    assert cp.current_l1 == 0
    assert cp.active_energy == pytest.approx(10562.978)
    assert cp.reactive_energy == pytest.approx(699.996)
    assert cp.apparent_energy == pytest.approx(10586.146)
    # The last session's energy stays after the vehicle has left.
    assert cp.session_energy == pytest.approx(42.952)
    assert cp.rfid_uid == "04A1B2C3D4E5F6"
    assert cp.evcc_id == ""
    assert cp.error_code == ErrorCode(0)
    # No PWM in status A: a duty cycle of 100 %.
    assert cp.charging_current_duty_cycle == 100
    assert cp.vehicle_status is VehicleStatus.A1
    assert not cp.is_connected


async def test_decodes_the_controls(real_unit: MockModbusUnit) -> None:
    cp = (await updated(real_unit)).charging_points[0]

    assert cp.charging_release is False
    # 0 outside Modbus release mode (docs/errata.md).
    assert cp.max_current == 0
    assert cp.available is True
    assert cp.watchdog_current == 16
    assert cp.watchdog_enabled is False


async def test_the_digital_outputs_follow_the_manuals_coding(real_unit: MockModbusUnit) -> None:
    # 0x1111: all four outputs in state 1, which the manual codes as floating, the state
    # of an output nothing drives (docs/errata.md, x302).
    cp = (await updated(real_unit)).charging_points[0]
    assert cp.digital_outputs is not None

    outputs = [DigitalOutputState((cp.digital_outputs >> (4 * n)) & 0xF) for n in range(4)]

    assert outputs == [DigitalOutputState.FLOATING] * 4


def test_the_dump_holds_every_mapped_register() -> None:
    # 26 global registers spanning 66 words, and 51 of a Charging Point spanning 100.
    assert len(REAL["registers"]["holding"]) == 66 + 100
