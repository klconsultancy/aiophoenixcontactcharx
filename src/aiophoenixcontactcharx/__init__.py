"""Async Python library for Phoenix Contact CHARX SEC EV charging controllers."""

from importlib.metadata import version

from .client import CharxClient
from .exceptions import (
    CharxConnectionError,
    CharxError,
    CharxInvalidDataError,
    CharxModbusError,
    CharxTimeoutError,
)
from .models import (
    ChargingPointConfig,
    ChargingPointControl,
    ChargingPointData,
    ChargingPointStatus,
    CharxData,
    DeviceInfo,
    DigitalOutputMode,
    EnergyMeterType,
    ErrorCode,
    ModemRegistration,
    ModemSignalQuality,
    OvercurrentMonitoring,
    ReleaseMode,
    TempMonitoring,
    VehicleStatus,
    pack_digital_outputs,
)
from .registers import RegisterDef, cp_register, offset_of

__version__ = version("aiophoenixcontactcharx")

__all__ = [
    "ChargingPointConfig",
    "ChargingPointControl",
    "ChargingPointData",
    "ChargingPointStatus",
    "CharxClient",
    "CharxConnectionError",
    "CharxData",
    "CharxError",
    "CharxInvalidDataError",
    "CharxModbusError",
    "CharxTimeoutError",
    "DeviceInfo",
    "DigitalOutputMode",
    "EnergyMeterType",
    "ErrorCode",
    "ModemRegistration",
    "ModemSignalQuality",
    "OvercurrentMonitoring",
    "RegisterDef",
    "ReleaseMode",
    "TempMonitoring",
    "VehicleStatus",
    "cp_register",
    "offset_of",
    "pack_digital_outputs",
]
