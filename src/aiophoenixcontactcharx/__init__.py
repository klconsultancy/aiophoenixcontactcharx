"""Async Python library for Phoenix Contact CHARX SEC EV charging controllers."""

from importlib.metadata import version

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
from .exceptions import CharxError
from .writing import CharxReleaseModeError, CharxWriteNotConfirmedError

__version__ = version("aiophoenixcontactcharx")

__all__ = [
    "MAX_CHARGING_POINTS",
    "ChargingInterface",
    "ChargingPoint",
    "CharxController",
    "CharxError",
    "CharxReleaseModeError",
    "CharxWriteNotConfirmedError",
    "ControllerInfo",
    "DigitalOutputState",
    "EnergyMeterType",
    "ErrorCode",
    "Group",
    "ModemRegistration",
    "ModemSignalQuality",
    "OvercurrentMonitoring",
    "ReleaseMode",
    "TempMonitoring",
    "VehicleStatus",
    "charging_point_name",
]
