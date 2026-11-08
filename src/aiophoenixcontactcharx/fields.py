"""The register fields CHARX needs beyond those of ``modbus_connection``.

Both are read-only and follow ``modbus_connection``'s extension pattern: a
``RegisterField`` subclass with its own ``decode``.
"""

import logging
from ipaddress import IPv4Address
from typing import override

from modbus_connection.model.fields import RegisterField

from .enums import VehicleStatus

_LOGGER = logging.getLogger(__name__)

# The number of registers of an IPv4 address: one octet per register.
IPV4_REGISTERS = 4
_OCTET_MAX = 0xFF


class IPv4OctetsField(RegisterField[IPv4Address]):
    """An IPv4 address over four registers, one octet in each.

    ``modbus_connection``'s ``IPv4Field`` packs the address into two registers; CHARX
    spends a register per octet (121-144). A register above 255 decodes to ``None``.
    """

    def __init__(self, address: int) -> None:
        """Declare the address at ``address`` and the three registers after it."""
        super().__init__(address, count=IPV4_REGISTERS)

    @override
    def decode(self, words: list[int], scale_exponent: int | None = None) -> IPv4Address | None:
        if any(word > _OCTET_MAX for word in words):
            _LOGGER.warning("Field %r: %s is no IPv4 address; decoding as None", self.name, words)
            return None
        return IPv4Address(bytes(words))


class VehicleStatusField(RegisterField[VehicleStatus]):
    """The IEC 61851-1 vehicle status: two ASCII characters in one register (x299).

    A register that holds no characters, or a code the enum doesn't know, decodes to
    ``None``; an unknown code is warned about once.
    """

    def __init__(self, address: int) -> None:
        """Declare the status at ``address``."""
        super().__init__(address)
        self._warned: set[int] = set()

    @override
    def decode(self, words: list[int], scale_exponent: int | None = None) -> VehicleStatus | None:
        (word,) = words
        code = word.to_bytes(2, "big").decode("ascii", errors="replace").strip("\x00 ")
        if not code:
            return None
        try:
            return VehicleStatus(code)
        except ValueError:
            if word not in self._warned:
                self._warned.add(word)
                _LOGGER.warning(
                    "Field %r: unknown vehicle status %r; decoding as None", self.name, code
                )
            return None
