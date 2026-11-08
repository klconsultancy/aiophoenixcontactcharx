"""Writing to the controller: validators, and a write that waits until it has landed.

A controller applies a write late (about 2 s) and answers a function code 06 write with
the register's old value (``docs/errata.md``, 167). So every write uses function code 16
(``force_fc16``), and a state write is read back until the controller reports the
written value.
"""

import asyncio
from collections.abc import Callable
from typing import Any, Final

from modbus_connection import ModbusUnit
from modbus_connection.model import Component

from .exceptions import CharxError

#: How long a write may take to land before it counts as not applied, in seconds.
CONFIRM_TIMEOUT: Final = 5.0
#: How often a write is read back while it hasn't landed, in seconds.
CONFIRM_INTERVAL: Final = 0.5

#: The range of a charging current the controller accepts (x301, x306): outside it, the
#: controller withdraws the charging release.
MIN_CURRENT: Final = 6
MAX_CURRENT: Final = 80
#: The largest value of a 16-bit register.
MAX_REGISTER: Final = 0xFFFF


class CharxReleaseModeError(CharxError):
    """A write needs a release mode the Charging Point isn't in."""


class CharxWriteNotConfirmedError(CharxError):
    """The controller didn't report the written value within the timeout."""


def int_in_range(low: int, high: int) -> Callable[[Any], int]:
    """Build a validator that accepts an int from ``low`` to ``high``.

    It raises ``TypeError`` for anything but an int (``bool`` included) and
    ``ValueError`` for an int outside the range.
    """

    def validate(value: Any) -> int:  # noqa: ANN401 (a validator takes what the caller passes)
        if isinstance(value, bool) or not isinstance(value, int):
            msg = f"must be an int, got {value!r}"
            raise TypeError(msg)
        if not low <= value <= high:
            msg = f"must be from {low} to {high}, got {value}"
            raise ValueError(msg)
        return value

    return validate


def a_bool(value: Any) -> bool:  # noqa: ANN401 (a validator takes what the caller passes)
    """Accept a ``bool``; raise ``TypeError`` for anything else."""
    if not isinstance(value, bool):
        msg = f"must be a bool, got {value!r}"
        raise TypeError(msg)
    return value


current_amps = int_in_range(MIN_CURRENT, MAX_CURRENT)
register_value = int_in_range(0, MAX_REGISTER)


_SAME: Final = object()


async def write_confirmed(  # noqa: PLR0913
    component: Component,
    field: str,
    value: object,
    *,
    expected: object = _SAME,
    confirm_within: float = CONFIRM_TIMEOUT,
    interval: float = CONFIRM_INTERVAL,
) -> None:
    """Write ``value`` to ``field`` of ``component`` and wait until it reads back.

    The component is read again until the field holds ``expected`` (by default
    ``value``; a sentinel that decodes to ``None`` passes ``None``), so on return its
    values are current. Raises ``TypeError`` or ``ValueError`` for a value the field's
    validator rejects (nothing is written), ``CharxWriteNotConfirmedError`` if the value
    hasn't landed after ``confirm_within`` seconds, and any ``ModbusError`` of the write or
    the reads.
    """
    if expected is _SAME:
        expected = value
    await component.write(field, value)
    # One deadline over every read and pause, so a read that stalls can't stretch it.
    deadline = asyncio.timeout(confirm_within)
    try:
        async with deadline:
            while True:
                await component.async_update()
                if getattr(component, field) == expected:
                    return
                await asyncio.sleep(interval)
    except TimeoutError:
        if not deadline.expired():
            raise  # a timeout of the Modbus read itself
        msg = (
            f"{field} reads {getattr(component, field)!r} {confirm_within} s after writing "
            f"{value!r}; the controller didn't apply the write"
        )
        raise CharxWriteNotConfirmedError(msg) from None


async def write_command(unit: ModbusUnit, address: int, value: int = 1) -> None:
    """Write ``value`` to the command register at ``address`` (function code 16).

    A command has no state to read back. Raises any ``ModbusError`` of the write.
    """
    await unit.write_registers(address, [value])
