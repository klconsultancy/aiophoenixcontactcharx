"""The ``aiophoenixcontactcharx`` command: read a controller and write what it holds as JSON.

The command only reads; it never writes to the controller.
"""

import argparse
import asyncio
import json
import sys
from collections.abc import Sequence
from enum import Enum, Flag
from ipaddress import IPv4Address
from pathlib import Path
from typing import Any

from modbus_connection import ModbusUnit
from modbus_connection.cli_helper import add_connection_args, connect_from_args
from modbus_connection.exceptions import ModbusConnectionError, ModbusError, ModbusTimeoutError
from modbus_connection.model import Component

from .controller import CharxController

# CHARX answers on Modbus server address 1 only (manual, table B-6).
UNIT_ID = 1


def _json_value(value: object) -> object:
    """Convert a decoded value to JSON: a flag to its member names, an enum to its name.

    A flag's bits that have no name (reserved, or new in a firmware) follow its names as
    one hexadecimal number, so a dump never hides an error bit.
    """
    if isinstance(value, Flag):
        names: list[object] = [member.name for member in value]
        named = 0
        for member in type(value):
            named |= member.value
        if unnamed := value.value & ~named:
            names.append(f"0x{unnamed:08X}")
        return names
    if isinstance(value, Enum):
        return value.name
    if isinstance(value, IPv4Address):
        return str(value)
    return value


def _values(component: Component) -> dict[str, object]:
    return {name: _json_value(getattr(component, name)) for name in component.declared_fields}


async def dump(unit: ModbusUnit) -> dict[str, Any]:
    """Read every mapped register and return it raw and decoded.

    A part whose read fails is left out of ``registers`` and ``values`` and listed under
    ``failed``. A lost connection or a timeout propagates.
    """
    controller = CharxController(unit)
    await controller.async_ensure_setup()
    raw: dict[int, int] = {}
    values: dict[str, dict[str, object]] = {}
    failed: dict[str, str] = {}
    parts: dict[str, Component] = {
        "device_info": controller.device_info,
        "group": controller.group,
        **{f"charging_point_{cp.number}": cp for cp in controller.charging_points},
    }
    for name, component in parts.items():
        try:
            registers = await component.async_read_raw(notify=False)
        except (ModbusConnectionError, ModbusTimeoutError):
            raise
        except ModbusError as err:
            failed[name] = str(err)
            continue
        raw.update(registers.get("holding", {}))
        values[name] = _values(component)
    return {
        "registers": {"holding": {str(address): raw[address] for address in sorted(raw)}},
        "values": values,
        "failed": failed,
    }


async def _dump_from_args(args: argparse.Namespace) -> dict[str, Any]:
    connection = await connect_from_args(args)
    try:
        return await dump(connection.for_unit(UNIT_ID))
    finally:
        await connection.close()


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command; return the exit status."""
    parser = argparse.ArgumentParser(
        prog="aiophoenixcontactcharx",
        description="Read a Phoenix Contact CHARX SEC charging controller over Modbus.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    dump_parser = commands.add_parser(
        "dump", help="read every register and write JSON (for bug reports and test fixtures)"
    )
    add_connection_args(dump_parser, connections=(("tcp", None),))
    dump_parser.add_argument(
        "-o", "--output", type=Path, default=None, help="write to this file instead of stdout"
    )
    args = parser.parse_args(argv)
    try:
        result = asyncio.run(_dump_from_args(args))
    except ModbusError as err:
        sys.stderr.write(f"aiophoenixcontactcharx: {err}\n")
        return 1
    text = json.dumps(result, indent=2) + "\n"
    if args.output is None:
        sys.stdout.write(text)
    else:
        args.output.write_text(text, encoding="utf-8")
    # The dump is written either way; a part that failed is in it under "failed".
    return 1 if result["failed"] else 0
