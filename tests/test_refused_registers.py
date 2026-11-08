"""A register the controller refuses is left out instead of failing its part (ADR 0006)."""

import logging

import pytest
from modbus_connection.exceptions import (
    IllegalDataAddressError,
    IllegalFunctionError,
    ModbusConnectionError,
    ModbusTimeoutError,
)
from modbus_connection.mock import MockModbusUnit

from aiophoenixcontactcharx import CharxController, VehicleStatus

# x262 (SOC energy) of Charging Point 2: a placeholder a firmware might not serve.
SOC_ENERGY = 2262


def read_addresses(unit: MockModbusUnit) -> set[int]:
    return {event.address + offset for event in unit.read_events for offset in range(event.count)}


@pytest.mark.parametrize("refusal", [IllegalDataAddressError(2), IllegalFunctionError(1)])
async def test_a_refused_register_is_left_out(
    controller_unit: MockModbusUnit,
    caplog: pytest.LogCaptureFixture,
    refusal: Exception,
) -> None:
    controller_unit.fail_read(SOC_ENERGY, refusal)
    controller = CharxController(controller_unit)

    report = await controller.async_update()

    assert report.complete
    cp = controller.charging_points[1]
    assert cp.soc_energy is None
    assert cp.vehicle_status is VehicleStatus.A1
    assert cp.active_energy == pytest.approx(812.0)
    assert (
        "The controller refuses register 2262 (charging_point_2.soc_energy); reading it as None"
        in caplog.text
    )


async def test_the_search_runs_once(controller_unit: MockModbusUnit) -> None:
    controller_unit.fail_read(SOC_ENERGY, IllegalDataAddressError(2))
    controller = CharxController(controller_unit)
    await controller.async_update()
    controller_unit.read_events.clear()

    report = await controller.async_update()

    assert report.complete
    assert SOC_ENERGY not in read_addresses(controller_unit)
    # The status range splits around the refused register: 2232-2261 and 2264-2307.
    assert sum(1 for event in controller_unit.read_events if event.address >= 2000) == 3


async def test_other_parts_are_not_searched(controller_unit: MockModbusUnit) -> None:
    controller_unit.fail_read(SOC_ENERGY, IllegalDataAddressError(2))
    controller = CharxController(controller_unit)

    await controller.async_update()

    # Charging Point 1 read its two ranges once; only Charging Point 2 was probed.
    point_1 = [event for event in controller_unit.read_events if 1000 <= event.address < 2000]
    assert len(point_1) == 2


async def test_a_part_whose_every_register_is_refused_reads_none(
    controller_unit: MockModbusUnit, caplog: pytest.LogCaptureFixture
) -> None:
    for address in range(147, 168):
        controller_unit.fail_read(address, IllegalDataAddressError(2))
    controller = CharxController(controller_unit)

    report = await controller.async_update()

    assert report.complete
    assert controller.group.active_power is None
    assert controller.group.dynamic_max_current is None
    assert "The controller refuses every register of group; reading it as None" in caplog.text


async def test_a_timeout_during_the_search_fails_only_the_part(
    controller_unit: MockModbusUnit,
) -> None:
    controller_unit.fail_read(SOC_ENERGY, IllegalDataAddressError(2))
    controller_unit.fail_read(2300, ModbusTimeoutError("slow"))
    controller = CharxController(controller_unit)

    report = await controller.async_update()

    assert isinstance(report.failed["charging_point_2"], ModbusTimeoutError)
    assert "charging_point_1" in report.updated


async def test_a_failed_search_is_tried_again(controller_unit: MockModbusUnit) -> None:
    controller_unit.fail_read(SOC_ENERGY, IllegalDataAddressError(2))
    controller_unit.fail_read(2300, ModbusTimeoutError("slow"))
    controller = CharxController(controller_unit)
    await controller.async_update()
    controller_unit.fail_read(2300, None)

    report = await controller.async_update()

    assert report.complete
    assert controller.charging_points[1].soc_energy is None
    assert controller.charging_points[1].charging_release is False


async def test_a_lost_connection_during_the_search_raises(
    controller_unit: MockModbusUnit,
) -> None:
    controller_unit.fail_read(SOC_ENERGY, IllegalDataAddressError(2))
    controller_unit.fail_read(2300, ModbusConnectionError("gone"))
    controller = CharxController(controller_unit)

    with pytest.raises(ModbusConnectionError):
        await controller.async_update()


async def test_a_failure_that_is_no_refusal_is_not_searched(
    controller_unit: MockModbusUnit,
) -> None:
    controller_unit.fail_read(SOC_ENERGY, ModbusTimeoutError("slow"))
    controller = CharxController(controller_unit)
    await controller.async_update()  # the timeout fails only charging_point_2
    controller_unit.read_events.clear()

    report = await controller.async_update()

    assert set(report.failed) == {"charging_point_2"}
    # One failed read of the status range, no field-by-field search.
    assert sum(1 for event in controller_unit.read_events if event.address >= 2000) == 2


async def test_a_timeout_on_the_retry_fails_only_its_part(
    controller_unit: MockModbusUnit, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Every part refuses a register, so the first poll answers nothing but refusals.
    for address in (145, 150, 1262, SOC_ENERGY):
        controller_unit.fail_read(address, IllegalDataAddressError(2))
    controller = CharxController(controller_unit)
    await controller.async_ensure_setup()
    # The retry of device_info, the first part read again, times out.
    original = controller.device_info.async_update
    calls = 0

    async def update(*, notify: bool = True) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:  # the retry
            msg = "slow"
            raise ModbusTimeoutError(msg)
        await original(notify=notify)

    monkeypatch.setattr(controller.device_info, "async_update", update)

    report = await controller.async_update()

    assert isinstance(report.failed["device_info"], ModbusTimeoutError)
    assert report.updated == {"group", "charging_point_1", "charging_point_2"}


# -- trying left-out registers again ------------------------------------------------


class Clock:
    """A clock the tests move by hand."""

    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


async def left_out_soc(unit: MockModbusUnit) -> tuple[CharxController, Clock]:
    """A controller that left out x262 of Charging Point 2, with a hand-moved clock."""
    unit.fail_read(SOC_ENERGY, IllegalDataAddressError(2))
    controller = CharxController(unit, retry_refused_after=60)
    clock = Clock()
    controller._clock = clock  # noqa: SLF001
    await controller.async_update()
    assert controller.charging_points[1].soc_energy is None
    return controller, clock


async def test_a_left_out_register_is_not_tried_before_its_time(
    controller_unit: MockModbusUnit,
) -> None:
    controller, clock = await left_out_soc(controller_unit)
    controller_unit.fail_read(SOC_ENERGY, None)
    clock.now += 59
    controller_unit.read_events.clear()

    await controller.async_update()

    assert SOC_ENERGY not in read_addresses(controller_unit)
    assert controller.charging_points[1].soc_energy is None


async def test_a_register_that_answers_again_is_put_back(
    controller_unit: MockModbusUnit, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO)
    controller, clock = await left_out_soc(controller_unit)
    controller_unit.fail_read(SOC_ENERGY, None)
    controller_unit.holding[SOC_ENERGY + 1] = 5
    clock.now += 60

    report = await controller.async_update()

    assert report.complete
    cp = controller.charging_points[1]
    assert cp.soc_energy == 5
    assert cp.vehicle_status is VehicleStatus.A1
    assert controller.charging_point_2 is cp  # type: ignore[attr-defined]
    assert "The controller answers register 2262 (charging_point_2.soc_energy) again" in (
        caplog.text
    )


async def test_the_controller_stops_trying_once_everything_is_back(
    controller_unit: MockModbusUnit,
) -> None:
    controller, clock = await left_out_soc(controller_unit)
    controller_unit.fail_read(SOC_ENERGY, None)
    clock.now += 60
    await controller.async_update()
    clock.now += 600
    controller_unit.read_events.clear()

    await controller.async_update()

    # Only the poll's reads: 3 global and 2 per Charging Point, no single-field probe.
    assert len(controller_unit.read_events) == 3 + 2 * 2


async def test_a_register_still_refused_stays_out_until_the_next_try(
    controller_unit: MockModbusUnit,
) -> None:
    controller, clock = await left_out_soc(controller_unit)
    clock.now += 60
    controller_unit.read_events.clear()

    report = await controller.async_update()

    assert report.complete
    assert (SOC_ENERGY, 2) in [(e.address, e.count) for e in controller_unit.read_events]
    assert controller.charging_points[1].soc_energy is None
    # Tried again only after another interval.
    clock.now += 30
    controller_unit.read_events.clear()
    await controller.async_update()
    assert SOC_ENERGY not in read_addresses(controller_unit)
    clock.now += 30
    controller_unit.fail_read(SOC_ENERGY, None)
    await controller.async_update()
    assert controller.charging_points[1].soc_energy == 0


async def test_one_of_two_left_out_registers_comes_back(
    controller_unit: MockModbusUnit,
) -> None:
    controller_unit.fail_read(SOC_ENERGY, IllegalDataAddressError(2))
    controller_unit.fail_read(2264, IllegalDataAddressError(2))  # SOC in %
    controller = CharxController(controller_unit, retry_refused_after=60)
    clock = Clock()
    controller._clock = clock  # noqa: SLF001
    await controller.async_update()
    controller_unit.fail_read(2264, None)
    controller_unit.holding[2264] = 42
    clock.now += 60

    report = await controller.async_update()

    assert report.complete
    cp = controller.charging_points[1]
    assert cp.soc == 42
    assert cp.soc_energy is None
    controller_unit.read_events.clear()
    await controller.async_update()
    assert SOC_ENERGY not in read_addresses(controller_unit)


async def test_a_left_out_part_comes_back_whole(controller_unit: MockModbusUnit) -> None:
    for address in range(147, 168):
        controller_unit.fail_read(address, IllegalDataAddressError(2))
    controller = CharxController(controller_unit, retry_refused_after=60)
    clock = Clock()
    controller._clock = clock  # noqa: SLF001
    await controller.async_update()
    assert controller.group.active_power is None
    for address in range(147, 168):
        controller_unit.fail_read(address, None)
    clock.now += 60

    await controller.async_update()

    assert controller.group.active_power == pytest.approx(7398.0)


async def test_a_timeout_on_the_retry_keeps_the_register_out(
    controller_unit: MockModbusUnit,
) -> None:
    controller, clock = await left_out_soc(controller_unit)
    controller_unit.fail_read(SOC_ENERGY, ModbusTimeoutError("slow"))
    clock.now += 60

    report = await controller.async_update()

    assert report.complete
    assert controller.charging_points[1].soc_energy is None


async def test_a_lost_connection_on_the_retry_raises(controller_unit: MockModbusUnit) -> None:
    controller, clock = await left_out_soc(controller_unit)
    controller_unit.fail_read(SOC_ENERGY, ModbusConnectionError("gone"))
    clock.now += 60

    with pytest.raises(ModbusConnectionError):
        await controller.async_update()


@pytest.mark.parametrize("seconds", [0, -1])
def test_the_retry_interval_must_be_positive(
    controller_unit: MockModbusUnit, seconds: float
) -> None:
    with pytest.raises(ValueError, match="retry_refused_after must be positive"):
        CharxController(controller_unit, retry_refused_after=seconds)


async def test_a_refusal_whose_fields_all_answer_alone_leaves_nothing_out(
    controller_unit: MockModbusUnit, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The block read is refused once, but every field answers on its own.
    controller = CharxController(controller_unit)
    await controller.async_ensure_setup()
    original = controller.group.async_update
    calls = 0

    async def update(*, notify: bool = True) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise IllegalDataAddressError(2)
        await original(notify=notify)

    monkeypatch.setattr(controller.group, "async_update", update)

    report = await controller.async_update()

    assert report.complete
    assert controller.group.active_power == pytest.approx(7398.0)
    assert controller._left_out == {}  # noqa: SLF001
