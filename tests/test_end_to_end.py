"""Run the library over real Modbus/TCP against an in-process tmodbus server.

The server replays a fixture and refuses every address the fixture doesn't hold, like a
controller that serves only what it has. No hardware is involved.
"""

import asyncio
import json
import socket
from collections.abc import AsyncIterator, Callable
from pathlib import Path
from typing import Any

import pytest
from modbus_connection import ModbusTcpParams
from modbus_connection.tmodbus import ModbusConnection
from tmodbus.exceptions import IllegalDataAddressError
from tmodbus.pdu import ReadHoldingRegistersPDU
from tmodbus.server import AsyncTcpServer, ModbusRequestRouter

from aiophoenixcontactcharx import CharxController, VehicleStatus, cli
from tests.conftest import REAL, SYNTHETIC


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port: int = probe.getsockname()[1]
        return port


def router_for(holding: dict[str, int]) -> ModbusRequestRouter:
    """Serve ``holding`` (a fixture's raw registers); refuse any other address."""
    router = ModbusRequestRouter()

    def serve() -> Callable[[int, ReadHoldingRegistersPDU], Any]:
        async def handle(_unit_id: int, request: ReadHoldingRegistersPDU) -> list[int]:
            addresses = range(request.start_address, request.start_address + request.quantity)
            if any(str(address) not in holding for address in addresses):
                raise IllegalDataAddressError(request.function_code)
            return [holding[str(address)] for address in addresses]

        return handle

    router.register(ReadHoldingRegistersPDU)(serve())
    return router


@pytest.fixture
async def synthetic_controller() -> AsyncIterator[int]:
    """The port of a server that replays the synthetic controller."""
    port = free_port()
    server = AsyncTcpServer("127.0.0.1", router_for(SYNTHETIC["registers"]["holding"]), port=port)
    await server.start()
    yield port
    await server.stop()


async def test_reads_the_controller_over_tcp(synthetic_controller: int) -> None:
    connection = ModbusConnection(ModbusTcpParams(host="127.0.0.1", port=synthetic_controller))
    await connection.connect()
    try:
        unit = connection.for_unit(cli.UNIT_ID)
        controller = CharxController(unit)
        report = await controller.async_update()

        # Every read stays within the fixture, so the server refused nothing.
        assert report.complete
        assert controller.device_info.designation == "CHARX SEC-3100"
        assert controller.charging_points[0].vehicle_status is VehicleStatus.C2
    finally:
        await connection.close()


async def test_dump_command_reads_the_controller_over_tcp(
    synthetic_controller: int, tmp_path: Path
) -> None:
    output = tmp_path / "charx.json"
    argv = ["dump", "127.0.0.1", "--port", str(synthetic_controller), "--output", str(output)]

    # The command runs its own event loop, so it runs beside the server's.
    status = await asyncio.to_thread(cli.main, argv)

    assert status == 0
    dump = json.loads(output.read_text(encoding="utf-8"))
    fixture = SYNTHETIC["registers"]["holding"]
    # Everything but the three command registers, which are never read.
    assert dump["registers"]["holding"] == {
        address: value
        for address, value in fixture.items()
        if address not in {"165", "166", "1308", "2308"}
    }


async def test_a_refused_register_is_left_out_over_tcp() -> None:
    # A firmware that lacks x262 (SOC) on Charging Point 2.
    holding = dict(SYNTHETIC["registers"]["holding"])
    del holding["2262"]
    del holding["2263"]
    port = free_port()
    server = AsyncTcpServer("127.0.0.1", router_for(holding), port=port)
    await server.start()
    connection = ModbusConnection(ModbusTcpParams(host="127.0.0.1", port=port))
    try:
        await connection.connect()
        controller = CharxController(connection.for_unit(cli.UNIT_ID))
        report = await controller.async_update()

        assert report.complete
        assert controller.charging_points[1].soc_energy is None
        assert controller.charging_points[1].vehicle_status is VehicleStatus.A1
    finally:
        await connection.close()
        await server.stop()


async def test_dumps_the_real_controller_as_it_was_dumped(tmp_path: Path) -> None:
    # The real dump, served back, dumps to the same registers: nothing more, nothing less.
    holding = REAL["registers"]["holding"]
    port = free_port()
    server = AsyncTcpServer("127.0.0.1", router_for(holding), port=port)
    await server.start()
    output = tmp_path / "charx.json"
    try:
        argv = ["dump", "127.0.0.1", "--port", str(port), "--output", str(output)]
        status = await asyncio.to_thread(cli.main, argv)
    finally:
        await server.stop()

    assert status == 0
    assert json.loads(output.read_text(encoding="utf-8"))["registers"]["holding"] == holding
