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
    EnergyMeterType,
    ModemRegistration,
    ModemSignalQuality,
    ReleaseMode,
    TempMonitoring,
    VehicleStatus,
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
    "EnergyMeterType",
    "ModemRegistration",
    "ModemSignalQuality",
    "ReleaseMode",
    "TempMonitoring",
    "VehicleStatus",
]
