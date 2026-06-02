"""aiophoenixcontactcharx — async Python library for Phoenix Contact CHARX SEC EV charging controllers."""

from .client import CharxClient
from .exceptions import (
    CharxConnectionError,
    CharxError,
    CharxInvalidDataError,
    CharxModbusError,
    CharxTimeoutError,
)
from .models import (
    CharxData,
    ChargingPointConfig,
    ChargingPointControl,
    ChargingPointData,
    ChargingPointStatus,
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

__version__ = "0.1.3"

__all__ = [
    "CharxClient",
    "CharxData",
    "CharxError",
    "CharxConnectionError",
    "CharxModbusError",
    "CharxTimeoutError",
    "CharxInvalidDataError",
    "ChargingPointConfig",
    "ChargingPointControl",
    "ChargingPointData",
    "ChargingPointStatus",
    "DeviceInfo",
    "DigitalOutputMode",
    "EnergyMeterType",
    "ErrorCode",
    "ModemRegistration",
    "ModemSignalQuality",
    "OvercurrentMonitoring",
    "pack_digital_outputs",
    "ReleaseMode",
    "TempMonitoring",
    "VehicleStatus",
]
