"""A register the controller refuses is left out instead of failing its part (ADR 0006)."""

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
