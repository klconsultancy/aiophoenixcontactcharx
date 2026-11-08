from typing import Any

import pytest
from modbus_connection.exceptions import IllegalDataAddressError, ModbusConnectionError
from modbus_connection.mock import MockModbusUnit, WriteEvent

from aiophoenixcontactcharx import (
    CharxController,
    CharxReleaseModeError,
    CharxWriteNotConfirmedError,
    DigitalOutputState,
)
from aiophoenixcontactcharx.writing import a_bool, int_in_range, write_confirmed

FC16 = 0x10


def recorded(unit: MockModbusUnit) -> list[WriteEvent]:
    events: list[WriteEvent] = []
    unit.on_write(events.append)
    return events


async def updated(unit: MockModbusUnit) -> CharxController:
    controller = CharxController(unit)
    report = await controller.async_update()
    assert report.complete
    return controller


# -- validators --------------------------------------------------------------------


def test_int_in_range_accepts_the_bounds() -> None:
    validate = int_in_range(6, 80)

    assert (validate(6), validate(80)) == (6, 80)


@pytest.mark.parametrize("value", [5, 81, -1])
def test_int_in_range_rejects_a_value_outside(value: int) -> None:
    with pytest.raises(ValueError, match="must be from 6 to 80"):
        int_in_range(6, 80)(value)


@pytest.mark.parametrize("value", [True, 16.0, "16", None])
def test_int_in_range_rejects_what_is_no_int(value: object) -> None:
    with pytest.raises(TypeError, match="must be an int"):
        int_in_range(6, 80)(value)


def test_a_bool_rejects_an_int() -> None:
    assert a_bool(True) is True  # noqa: FBT003
    with pytest.raises(TypeError, match="must be a bool"):
        a_bool(1)


# -- confirming a write ------------------------------------------------------------


async def test_a_write_uses_function_code_16(controller_unit: MockModbusUnit) -> None:
    group = (await updated(controller_unit)).group
    events = recorded(controller_unit)

    await group.set_dynamic_max_current(20)

    assert [(e.address, e.values, e.function_code) for e in events] == [(167, [20], FC16)]
    assert group.dynamic_max_current == 20  # read back: the cache is current


def landing_late(unit: MockModbusUnit, address: int, *, after_reads: int) -> None:
    """Make a write to ``address`` read back only after ``after_reads`` more reads."""
    old = unit.holding[address]

    def hold_back(event: WriteEvent) -> None:
        written = event.values[0]
        unit.holding[address] = old
        reads = 0

        def value() -> Any:  # noqa: ANN401
            nonlocal reads
            reads += 1
            return written if reads > after_reads else old

        unit.holding[address] = value

    unit.on_write(hold_back)


async def test_a_write_that_lands_late_is_waited_for(controller_unit: MockModbusUnit) -> None:
    group = (await updated(controller_unit)).group
    landing_late(controller_unit, 167, after_reads=3)

    await write_confirmed(group, "dynamic_max_current", 20, interval=0)

    assert group.dynamic_max_current == 20


async def test_a_write_that_never_lands_raises(controller_unit: MockModbusUnit) -> None:
    group = (await updated(controller_unit)).group
    landing_late(controller_unit, 167, after_reads=10**6)

    with pytest.raises(CharxWriteNotConfirmedError, match="dynamic_max_current reads 32"):
        await write_confirmed(group, "dynamic_max_current", 20, confirm_within=0.05, interval=0)


async def test_a_rejected_value_writes_nothing(controller_unit: MockModbusUnit) -> None:
    cp = (await updated(controller_unit)).charging_points[0]
    events = recorded(controller_unit)

    with pytest.raises(ValueError, match="must be from 6 to 80"):
        await cp.set_max_current(81)

    assert events == []


async def test_a_refused_write_raises(controller_unit: MockModbusUnit) -> None:
    group = (await updated(controller_unit)).group
    controller_unit.fail_write(164, IllegalDataAddressError(2))

    with pytest.raises(IllegalDataAddressError):
        await group.set_available(False)


async def test_a_lost_connection_during_a_write_raises(controller_unit: MockModbusUnit) -> None:
    group = (await updated(controller_unit)).group
    controller_unit.fail_write(167, ModbusConnectionError("gone"))

    with pytest.raises(ModbusConnectionError):
        await group.set_dynamic_max_current(20)


# -- the Group ---------------------------------------------------------------------


async def test_clearing_the_dynamic_limit_writes_65535(controller_unit: MockModbusUnit) -> None:
    group = (await updated(controller_unit)).group
    events = recorded(controller_unit)

    await group.set_dynamic_max_current(None)

    assert [(e.address, e.values) for e in events] == [(167, [65535])]
    assert group.dynamic_max_current is None


async def test_65535_is_no_dynamic_limit(controller_unit: MockModbusUnit) -> None:
    group = (await updated(controller_unit)).group

    with pytest.raises(ValueError, match="pass None to clear the limit"):
        await group.set_dynamic_max_current(65535)


async def test_the_dynamic_limit_works_in_ocpp_release_mode(real_unit: MockModbusUnit) -> None:
    # As tested on the real controller (docs/errata.md, 167).
    group = (await updated(real_unit)).group

    await group.set_dynamic_max_current(16)

    assert group.dynamic_max_current == 16


async def test_the_group_goes_out_of_service(controller_unit: MockModbusUnit) -> None:
    group = (await updated(controller_unit)).group

    await group.set_available(False)

    assert group.available is False


# -- a Charging Point --------------------------------------------------------------


@pytest.mark.parametrize(
    ("method", "value", "address", "field", "written"),
    [
        ("set_charging_release", False, 1300, "charging_release", 0),
        ("set_available", False, 1304, "available", 0),
        ("set_max_current", 10, 1301, "max_current", 10),
        ("set_locked", False, 1303, "locked", 0),
        ("set_watchdog_current", 8, 1306, "watchdog_current", 8),
        ("set_watchdog_timer", 30, 1307, "watchdog_timer", 30),
    ],
)
async def test_a_control_writes_its_register_and_reads_it_back(  # noqa: PLR0913
    controller_unit: MockModbusUnit,
    *,
    method: str,
    value: object,
    address: int,
    field: str,
    written: int,
) -> None:
    # The synthetic Charging Point 1 is in release mode Modbus.
    cp = (await updated(controller_unit)).charging_points[0]
    events = recorded(controller_unit)

    await getattr(cp, method)(value)

    assert [(e.address, e.values, e.function_code) for e in events] == [(address, [written], FC16)]
    assert getattr(cp, field) == value


@pytest.mark.parametrize("method", ["set_charging_release", "set_available"])
async def test_release_and_availability_need_release_mode_modbus(
    real_unit: MockModbusUnit, method: str
) -> None:
    # The real Charging Point is in OCPP release mode.
    cp = (await updated(real_unit)).charging_points[0]
    events = recorded(real_unit)

    with pytest.raises(CharxReleaseModeError, match="Charging Point 1 is in release mode OCPP"):
        await getattr(cp, method)(True)  # noqa: FBT003

    assert events == []


async def test_an_unread_release_mode_refuses_the_release(
    controller_unit: MockModbusUnit,
) -> None:
    controller = await updated(controller_unit)
    cp = type(controller.charging_points[0])(controller_unit, 1, base_offset=1000)

    with pytest.raises(CharxReleaseModeError, match="an unread release mode"):
        await cp.set_charging_release(True)


async def test_the_max_current_works_in_ocpp_release_mode(real_unit: MockModbusUnit) -> None:
    # The manual sets no condition on x301; on hardware it is unverified (docs/errata.md).
    cp = (await updated(real_unit)).charging_points[0]

    await cp.set_max_current(16)

    assert cp.max_current == 16


async def test_the_digital_outputs_are_packed_output_1_first(
    controller_unit: MockModbusUnit,
) -> None:
    cp = (await updated(controller_unit)).charging_points[0]
    events = recorded(controller_unit)

    await cp.set_digital_outputs(
        DigitalOutputState.FLOATING,
        DigitalOutputState.LOW,
        DigitalOutputState.FLASHING_LOW,
        DigitalOutputState.HIGH,
    )

    assert [(e.address, e.values) for e in events] == [(1302, [0x5321])]


async def test_the_digital_outputs_need_four_states(controller_unit: MockModbusUnit) -> None:
    cp = (await updated(controller_unit)).charging_points[0]

    with pytest.raises(ValueError, match="give 4 states"):
        await cp.set_digital_outputs(DigitalOutputState.LOW)


async def test_none_disables_the_watchdog(controller_unit: MockModbusUnit) -> None:
    cp = (await updated(controller_unit)).charging_points[0]

    await cp.set_watchdog_timer(None)

    assert cp.watchdog_timer == 65535
    assert cp.watchdog_enabled is False


async def test_65535_is_no_watchdog_interval(controller_unit: MockModbusUnit) -> None:
    cp = (await updated(controller_unit)).charging_points[0]

    with pytest.raises(ValueError, match="pass None to disable the watchdog"):
        await cp.set_watchdog_timer(65535)


@pytest.mark.parametrize("amps", [5, 81])
async def test_the_watchdog_current_is_6_to_80(controller_unit: MockModbusUnit, amps: int) -> None:
    cp = (await updated(controller_unit)).charging_points[0]

    with pytest.raises(ValueError, match="must be from 6 to 80"):
        await cp.set_watchdog_current(amps)


# -- commands ----------------------------------------------------------------------


async def test_enforcing_unlocking_writes_1_without_reading_back(
    controller_unit: MockModbusUnit,
) -> None:
    cp = (await updated(controller_unit)).charging_points[1]
    events = recorded(controller_unit)
    controller_unit.read_events.clear()

    await cp.enforce_unlocking()

    assert [(e.address, e.values, e.function_code) for e in events] == [(2305, [1], FC16)]
    assert controller_unit.read_events == []


async def test_clearing_the_last_rfid_writes_its_command_register(
    controller_unit: MockModbusUnit,
) -> None:
    cp = (await updated(controller_unit)).charging_points[1]
    events = recorded(controller_unit)

    await cp.clear_last_rfid()

    assert [(e.address, e.values, e.function_code) for e in events] == [(2308, [1], FC16)]


@pytest.mark.parametrize(("method", "address"), [("reset", 165), ("system_reset", 166)])
async def test_a_reset_writes_its_command_register(
    controller_unit: MockModbusUnit, method: str, address: int
) -> None:
    controller = await updated(controller_unit)
    events = recorded(controller_unit)

    await getattr(controller, method)()

    assert [(e.address, e.values, e.function_code) for e in events] == [(address, [1], FC16)]
