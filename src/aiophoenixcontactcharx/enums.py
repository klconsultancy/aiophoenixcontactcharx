"""The value codings of the CHARX Modbus registers (UM EN CHARX SEC, Appendix B3).

Each enum's values are the register values the manual lists. Where the controller
differs from the manual, ``docs/errata.md`` says so.
"""

from enum import IntEnum, IntFlag, StrEnum


class ErrorCode(IntFlag):
    """The error bits of a Charging Point (x293-x294; manual B1, "Error codes").

    Python counts bits from 0 (bit N is ``1 << N``), the manual from 1 (its bit M is
    Python's bit M-1). Python bit 2 and bits 7-15 are reserved. A bit a later firmware
    adds stays in the value: an ``IntFlag`` keeps unknown bits.
    """

    TEMPERATURE_TOO_HIGH = 1 << 0
    TEMPERATURE_DERATING = 1 << 1
    CONFIGURATION_ERROR = 1 << 3
    LOAD_MANAGEMENT_PAUSED = 1 << 4
    EVENT_ACTIONS_UNCLEAR = 1 << 5
    RFID_READER_ERROR = 1 << 6
    CONNECTOR_13A_20A_REJECTED = 1 << 16
    CONNECTOR_13A_REJECTED = 1 << 17
    PP_ERROR = 1 << 18
    CP_ERROR = 1 << 19
    VEHICLE_ERROR_F = 1 << 20
    LOCKING_ERROR = 1 << 21
    LOCK_RELEASE_ERROR = 1 << 22
    UNKNOWN_LOCKING_STATE = 1 << 23
    OVERCURRENT_DETECTED = 1 << 24
    ENERGY_METER_COMM_ERROR = 1 << 25
    INVALID_STATUS_D = 1 << 26
    CONTACTOR_ERROR = 1 << 27
    EV_DIODE_ERROR = 1 << 28
    POWER_SUPPLY_ERROR = 1 << 29
    RESIDUAL_CURRENT_TRIP = 1 << 30
    RESIDUAL_CURRENT_SENSOR_ERROR = 1 << 31


class ChargingInterface(IntEnum):
    """The charging interface per IEC 61851-1 (x100)."""

    SOCKET = 0  # charging case B
    CONNECTOR = 1  # charging case C


class DigitalOutputState(IntEnum):
    """The state of one digital output (x302, 4 bits per output)."""

    UNDEFINED = 0
    FLOATING = 1
    LOW = 2
    FLASHING_LOW = 3
    PULSATING_LOW = 4
    HIGH = 5
    FLASHING_HIGH = 6


class ReleaseMode(IntEnum):
    """What authorizes charging on a Charging Point (x120)."""

    DASHBOARD = 0
    LOCAL_WHITELIST = 1
    EXTERNAL_CONTROL = 2
    PERMANENT = 3
    OCPP = 4
    MODBUS = 5


class EnergyMeterType(IntEnum):
    """The energy measuring device of a Charging Point (x112); 5 and 7-10 are reserved."""

    NONE = 0
    EEM_350_D_MCB = 1
    EEM_EM357 = 2
    CARLO_GAVAZZI_EM24 = 3
    EEM_EM357_EE = 4
    CARLO_GAVAZZI_EM340 = 6
    ISKRA_WM3M4 = 11
    INEPRO_PRO380 = 12
    UNKNOWN = 65535


class ModemRegistration(IntEnum):
    """The modem's registration status (145)."""

    NOT_REGISTERED = 0
    REGISTERED = 1
    SEARCHING = 2
    DENIED = 3
    UNKNOWN = 4


class ModemSignalQuality(IntEnum):
    """The modem's signal quality (146)."""

    UNKNOWN = 0
    INADEQUATE_TO_NONE = 1
    INADEQUATE = 2
    OK = 3
    GOOD = 4
    EXCELLENT = 5


class OvercurrentMonitoring(IntEnum):
    """Overcurrent monitoring of a Charging Point (x111)."""

    OFF = 0
    PCT120_10S = 1  # shutdown at 120 % for 10 s and 110 % for 100 s
    EV_ZE_READY = 2


class TempMonitoring(IntEnum):
    """Temperature monitoring of a Charging Point (x108)."""

    INACTIVE = 0
    PT1000 = 1
    PTC = 2


class VehicleStatus(StrEnum):
    """The IEC 61851-1 status of a Charging Point (x299), two ASCII characters."""

    A1 = "A1"  # not connected, supply available
    A2 = "A2"  # not connected, supply not available
    B1 = "B1"  # connected, supply available
    B2 = "B2"  # connected, supply not available
    C1 = "C1"  # charging requested, no ventilation required
    C2 = "C2"  # charging
    D1 = "D1"  # charging requested with ventilation, none available
    D2 = "D2"  # charging with ventilation
    E0 = "E0"  # error
    F0 = "F0"  # not available (status F)
    IN = "IN"  # initialising
