"""The library's own exceptions.

A Modbus failure raises ``modbus_connection``'s exceptions (``ModbusConnectionError``,
``ModbusTimeoutError``, ``IllegalDataAddressError``, ...), which the library doesn't wrap.
"""


class CharxError(Exception):
    """The base of the library's own exceptions."""
