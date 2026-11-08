"""Exceptions for the aiophoenixcontactcharx library."""


class CharxError(Exception):
    """Base exception for all CHARX errors."""


class CharxConnectionError(CharxError):
    """Raised when a connection to the CHARX controller cannot be established."""


class CharxTimeoutError(CharxConnectionError):
    """Raised when a connection or operation times out."""


class CharxModbusError(CharxError):
    """Raised when a Modbus protocol error is returned by the device."""


class CharxInvalidDataError(CharxModbusError):
    """Raised when the device returns data that cannot be parsed."""
