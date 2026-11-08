"""Fixtures for the tests of the 2.0 register map."""

import json
from pathlib import Path
from typing import Any

import pytest
from modbus_connection.mock import MockModbusUnit

FIXTURES = Path(__file__).parent / "fixtures"

# A two-point controller: Charging Point 1 charges, 2 has no vehicle (see its "source").
SYNTHETIC: dict[str, Any] = json.loads(
    (FIXTURES / "synthetic-sec3100.json").read_text(encoding="utf-8")
)


# A real controller, anonymized: firmware 1.7.3, one Charging Point, no vehicle.
REAL: dict[str, Any] = json.loads((FIXTURES / "sec3xxx-1.7.3.json").read_text(encoding="utf-8"))


@pytest.fixture
def real_unit(mock_modbus_unit: MockModbusUnit) -> MockModbusUnit:
    """A mock unit that answers like the real controller."""
    mock_modbus_unit.load_raw(REAL["registers"])
    return mock_modbus_unit


@pytest.fixture
def controller_unit(mock_modbus_unit: MockModbusUnit) -> MockModbusUnit:
    """A mock unit that answers like the synthetic controller."""
    mock_modbus_unit.load_raw(SYNTHETIC["registers"])
    return mock_modbus_unit
