import json
from collections.abc import Iterator
from importlib.metadata import entry_points
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from modbus_connection.exceptions import (
    IllegalDataAddressError,
    ModbusConnectionError,
    ModbusTimeoutError,
)
from modbus_connection.mock import MockModbusConnection, MockModbusUnit

from aiophoenixcontactcharx import cli
from tests.conftest import SYNTHETIC


async def test_dump_holds_the_registers_and_the_values(controller_unit: MockModbusUnit) -> None:
    dump = await cli.dump(controller_unit)

    registers = dump["registers"]["holding"]
    assert registers["114"] == 2
    assert registers["1299"] == SYNTHETIC["registers"]["holding"]["1299"]
    values = dump["values"]
    assert values["device_info"]["designation"] == "CHARX SEC-3100"
    assert values["device_info"]["ip_eth0"] == "192.168.1.50"
    assert values["device_info"]["modem_registration"] == "UNKNOWN"
    assert values["charging_point_1"]["vehicle_status"] == "C2"
    assert values["charging_point_2"]["error_code"] == ["RFID_READER_ERROR"]
    assert values["group"]["current_l1"] is None
    assert dump["failed"] == {}
    json.dumps(dump)  # serializable as it is


async def test_dump_reads_only_mapped_addresses(controller_unit: MockModbusUnit) -> None:
    dump = await cli.dump(controller_unit)

    # The commands are in the fixture but never read.
    assert {"165", "166", "1308", "2308"}.isdisjoint(dump["registers"]["holding"])


async def test_dump_lists_a_failed_part_and_keeps_the_rest(
    controller_unit: MockModbusUnit,
) -> None:
    controller_unit.fail_read(2232, IllegalDataAddressError(3))

    dump = await cli.dump(controller_unit)

    assert set(dump["failed"]) == {"charging_point_2"}
    assert "charging_point_2" not in dump["values"]
    assert "charging_point_1" in dump["values"]


async def test_dump_propagates_a_lost_connection(controller_unit: MockModbusUnit) -> None:
    controller_unit.fail_requests(ModbusConnectionError("gone"))

    with pytest.raises(ModbusConnectionError):
        await cli.dump(controller_unit)


async def test_dump_propagates_a_timeout_after_the_setup(controller_unit: MockModbusUnit) -> None:
    # The identity answered; then the controller stops answering.
    controller_unit.fail_read(147, ModbusTimeoutError("silent"))

    with pytest.raises(ModbusTimeoutError):
        await cli.dump(controller_unit)


@pytest.fixture
def connection() -> Iterator[MockModbusConnection]:
    """The connection ``main`` opens, answering like the synthetic controller."""
    mock = MockModbusConnection()
    mock.for_unit(cli.UNIT_ID).load_raw(SYNTHETIC["registers"])
    with patch.object(cli, "connect_from_args", AsyncMock(return_value=mock)) as connect:
        yield mock
    connect.assert_awaited_once()


def test_main_writes_the_dump_to_stdout(
    connection: MockModbusConnection, capsys: pytest.CaptureFixture[str]
) -> None:
    assert cli.main(["dump", "192.168.1.50"]) == 0

    assert json.loads(capsys.readouterr().out)["values"]["device_info"]["charging_controllers"] == 2
    assert not connection.connected  # closed afterwards


@pytest.mark.usefixtures("connection")
def test_main_writes_the_dump_to_a_file(tmp_path: Path) -> None:
    output = tmp_path / "charx.json"

    assert cli.main(["dump", "192.168.1.50", "--output", str(output)]) == 0

    assert json.loads(output.read_text(encoding="utf-8"))["failed"] == {}


def test_main_exits_1_when_a_part_failed(
    connection: MockModbusConnection, capsys: pytest.CaptureFixture[str]
) -> None:
    connection.for_unit(cli.UNIT_ID).fail_read(1232, IllegalDataAddressError(3))

    assert cli.main(["dump", "192.168.1.50"]) == 1

    assert "charging_point_1" in json.loads(capsys.readouterr().out)["failed"]


def test_main_exits_1_without_a_dump_when_the_link_is_down(
    connection: MockModbusConnection, capsys: pytest.CaptureFixture[str]
) -> None:
    connection.for_unit(cli.UNIT_ID).fail_requests(ModbusConnectionError("gone"))

    assert cli.main(["dump", "192.168.1.50"]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "aiophoenixcontactcharx: gone" in captured.err


def test_main_offers_tcp_only(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        cli.main(["dump", "/dev/ttyUSB0", "--transport", "serial"])

    assert "unrecognized arguments: --transport serial" in capsys.readouterr().err


def test_the_command_is_installed() -> None:
    (command,) = entry_points(group="console_scripts", name="aiophoenixcontactcharx")

    assert command.value == "aiophoenixcontactcharx.cli:main"
