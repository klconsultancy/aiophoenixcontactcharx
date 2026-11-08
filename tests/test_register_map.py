"""Check the register map against the manual's tables, in both directions.

``docs/protocol/B3-modbus.md`` transcribes Appendix B3 of UM EN CHARX SEC, Revision 08.
Table B-7 lists the global registers (0-999), table B-8 those of one Charging Point at
the offsets of its x000 block.
"""

import re
from pathlib import Path
from typing import Any, NamedTuple

import pytest
from modbus_connection.model import Component
from modbus_connection.model.fields import RegisterField

from aiophoenixcontactcharx import ChargingPoint, ControllerInfo, Group

MANUAL = Path(__file__).parents[1] / "docs" / "protocol" / "B3-modbus.md"

# The registers that are commands rather than state. They are written, never read, and
# come with the write API.
COMMANDS: dict[tuple[str, int], str] = {
    ("global", 165): "reset: restarts the server",
    ("global", 166): "system reset: restarts every controller of the group",
    ("point", 308): "clears the last RFID UID (x275); reads back 0",
}

_ROW = re.compile(r"^\| (?P<x>[Xx]?)(?P<address>\d+) \| (?P<words>\d+) \| (?P<access>[^|]+) \|")


class Row(NamedTuple):
    words: int
    access: str


def documented() -> dict[tuple[str, int], Row]:
    """Every register row of tables B-7 and B-8, keyed by table and address."""
    rows: dict[tuple[str, int], Row] = {}
    for line in MANUAL.read_text(encoding="utf-8").splitlines():
        if match := _ROW.match(line):
            table = "point" if match["x"] else "global"
            # A register with several codings has a row per coding; they agree.
            row = Row(int(match["words"]), match["access"].strip())
            rows.setdefault((table, int(match["address"])), row)
    return rows


MAPPED: dict[str, tuple[type[Component], ...]] = {
    "global": (ControllerInfo, Group),
    "point": (ChargingPoint,),
}


def mapped() -> dict[tuple[str, int], tuple[str, RegisterField[Any]]]:
    """Every field of the map, keyed like ``documented()``, with its qualified name."""
    fields: dict[tuple[str, int], tuple[str, RegisterField[Any]]] = {}
    for table, components in MAPPED.items():
        for component in components:
            for name, field in component.declared_fields.items():
                assert isinstance(field, RegisterField)
                key = (table, field.address)
                assert key not in fields, f"{name} shares {key} with {fields[key][0]}"
                fields[key] = (f"{component.__name__}.{name}", field)
    return fields


def test_the_manual_lists_both_tables() -> None:
    rows = documented()

    assert sum(table == "global" for table, _ in rows) == 28
    assert sum(table == "point" for table, _ in rows) == 52


@pytest.mark.parametrize(("key", "field"), sorted(mapped().items()), ids=str)
def test_every_field_is_documented_with_its_width(
    key: tuple[str, int], field: tuple[str, RegisterField[Any]]
) -> None:
    name, register = field
    row = documented().get(key)

    assert row is not None, f"{name} is at {key}, which the manual doesn't list"
    assert register.count == row.words, f"{name} spans {register.count}, the manual {row.words}"


def test_every_documented_register_is_mapped_or_a_command() -> None:
    missing = set(documented()) - set(mapped()) - set(COMMANDS)

    assert not missing, f"documented but not mapped: {sorted(missing)}"


def test_no_command_is_mapped() -> None:
    assert set(COMMANDS).isdisjoint(mapped())
    assert set(COMMANDS) <= set(documented())


def _spans(component: type[Component]) -> tuple[tuple[int, int], ...]:
    """The fields' addresses merged into contiguous ranges, as ``register_ranges`` states."""
    spans: list[list[int]] = []
    for field in sorted(component.declared_fields.values(), key=lambda f: f.address):
        assert isinstance(field, RegisterField)
        end = field.address + field.count - 1
        if spans and field.address == spans[-1][1] + 1:
            spans[-1][1] = end
        else:
            spans.append([field.address, end])
    return tuple((start, end) for start, end in spans)


@pytest.mark.parametrize("component", [ControllerInfo, Group, ChargingPoint])
def test_the_read_ranges_are_exactly_the_mapped_fields(component: type[Component]) -> None:
    # So a read covers only documented addresses, and every one of them.
    assert component.register_ranges == _spans(component)
