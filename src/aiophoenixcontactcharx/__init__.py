"""Async Python library for Phoenix Contact CHARX SEC EV charging controllers."""

from importlib.metadata import version

from .client import CharxClient
from .controller import (
    MAX_CHARGING_POINTS,
    ChargingPoint,
    CharxController,
    ControllerInfo,
    Group,
    charging_point_name,
)
from .enums import (
    ChargingInterface,
    DigitalOutputState,
    EnergyMeterType,
    ErrorCode,
    ModemRegistration,
    ModemSignalQuality,
    OvercurrentMonitoring,
    ReleaseMode,
    TempMonitoring,
    VehicleStatus,
)
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
    pack_digital_outputs,
)
from .registers import RegisterDef, cp_register, offset_of

__version__ = version("aiophoenixcontactcharx")

__all__ = [
    "MAX_CHARGING_POINTS",
    "ChargingInterface",
    "ChargingPoint",
    "ChargingPointConfig",
    "ChargingPointControl",
    "ChargingPointData",
    "ChargingPointStatus",
    "CharxClient",
    "CharxConnectionError",
    "CharxController",
    "CharxData",
    "CharxError",
    "CharxInvalidDataError",
    "CharxModbusError",
    "CharxTimeoutError",
    "ControllerInfo",
    "DeviceInfo",
    "DigitalOutputMode",
    "DigitalOutputState",
    "EnergyMeterType",
    "ErrorCode",
    "Group",
    "ModemRegistration",
    "ModemSignalQuality",
    "OvercurrentMonitoring",
    "RegisterDef",
    "ReleaseMode",
    "TempMonitoring",
    "VehicleStatus",
    "charging_point_name",
    "cp_register",
    "offset_of",
    "pack_digital_outputs",
]
