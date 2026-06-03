"""Modbus register addresses for Phoenix Contact CHARX SEC EV charging controllers.

Source: UM EN CHARX SEC, Revision 08 — Appendix B3, p. 167–174.
All addresses are 0-indexed Modbus PDU addresses (as used by pymodbus).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RegisterDef:
    """Metadata for a single Modbus register (or contiguous multi-word field)."""
    address: int
    width: int       # number of 16-bit registers
    description: str = ""


def offset_of(reg: RegisterDef, base: RegisterDef) -> int:
    """Array offset of *reg* relative to *base* (reg.address − base.address)."""
    result = reg.address - base.address
    if result < 0:
        raise ValueError(
            f"{reg!r} (address {reg.address}) precedes base {base!r} (address {base.address})"
        )
    return result


# ---------------------------------------------------------------------------
# Global registers (address range 100–167)
# Applies to the entire group (server + all clients + backplane modules).
# ---------------------------------------------------------------------------

DEVICE_DESIGNATION       = RegisterDef(100, 10, "ASCII designation (20 chars)")
SOFTWARE_VERSION         = RegisterDef(110,  4, "ASCII software version (8 chars)")
NUM_CONTROLLERS          = RegisterDef(114,  1, "Number of connected controllers")
MAC_ETH0                 = RegisterDef(115,  3, "MAC address ETH0 (3 × HEX word)")
MAC_ETH1                 = RegisterDef(118,  3, "MAC address ETH1")
IP_ETH0                  = RegisterDef(121,  4, "IP address ETH0 (4 × octet)")
IP_ETH1                  = RegisterDef(125,  4, "IP address ETH1")
SUBNET_ETH0              = RegisterDef(129,  4, "Subnet mask ETH0")
SUBNET_ETH1              = RegisterDef(133,  4, "Subnet mask ETH1")
GATEWAY_ETH0             = RegisterDef(137,  4, "Default gateway ETH0 (placeholder, returns 0)")
GATEWAY_ETH1             = RegisterDef(141,  4, "Default gateway ETH1 (placeholder, returns 0)")
MODEM_REGISTRATION       = RegisterDef(145,  1, "Modem registration status")
MODEM_SIGNAL_QUALITY     = RegisterDef(146,  1, "Modem signal quality")
NUM_NON_CRITICAL_ERROR   = RegisterDef(147,  1, "Count of non-critical errors in group")
NUM_STATUS_EF            = RegisterDef(148,  1, "Count of CPs in status E/F")
NUM_STATUS_A             = RegisterDef(149,  1, "Count of CPs in status A")
NUM_STATUS_BCD           = RegisterDef(150,  1, "Count of CPs in status B/C/D")
NUM_CHARGING             = RegisterDef(151,  1, "Count of active C2 charging sessions")
GROUP_ACTIVE_POWER       = RegisterDef(152,  2, "Group active power [mW]")
GROUP_REACTIVE_POWER     = RegisterDef(154,  2, "Group reactive power [mVAR] (signed)")
GROUP_APPARENT_POWER     = RegisterDef(156,  2, "Group apparent power [mVA]")
GROUP_CURRENT_L1         = RegisterDef(158,  2, "Group current L1 [mA]; −1 if phase unknown")
GROUP_CURRENT_L2         = RegisterDef(160,  2, "Group current L2 [mA]")
GROUP_CURRENT_L3         = RegisterDef(162,  2, "Group current L3 [mA]")
_GROUP_AVAILABILITY_REG  = RegisterDef(164,  1, "Group availability (R/W if configured)")
_GROUP_RESET_REG         = RegisterDef(165,  1, "Restart server only (W)")
_GROUP_SYSTEM_RESET_REG  = RegisterDef(166,  1, "Restart all controllers (W)")
_GROUP_DYNAMIC_MAX_REG   = RegisterDef(167,  1, "Dynamic max current for load management (R/W) [A]")

GLOBAL_REGISTERS: tuple[RegisterDef, ...] = (
    DEVICE_DESIGNATION, SOFTWARE_VERSION, NUM_CONTROLLERS,
    MAC_ETH0, MAC_ETH1,
    IP_ETH0, IP_ETH1,
    SUBNET_ETH0, SUBNET_ETH1,
    GATEWAY_ETH0, GATEWAY_ETH1,
    MODEM_REGISTRATION, MODEM_SIGNAL_QUALITY,
    NUM_NON_CRITICAL_ERROR, NUM_STATUS_EF, NUM_STATUS_A, NUM_STATUS_BCD, NUM_CHARGING,
    GROUP_ACTIVE_POWER, GROUP_REACTIVE_POWER, GROUP_APPARENT_POWER,
    GROUP_CURRENT_L1, GROUP_CURRENT_L2, GROUP_CURRENT_L3,
    _GROUP_AVAILABILITY_REG, _GROUP_RESET_REG, _GROUP_SYSTEM_RESET_REG, _GROUP_DYNAMIC_MAX_REG,
)

# ---------------------------------------------------------------------------
# Per-charging-point register offsets
# Absolute address = charging_point_number × 1000 + offset.
# Default start addresses: CP1 → 1000, CP2 → 2000, … CP12 → 12000.
# ---------------------------------------------------------------------------

# Configuration (offsets 100–123 within the x000 block)
CP_INTERFACE_CONFIG      = RegisterDef(100, 1, "Interface config: 0=socket, 1=connector")
CP_MAX_CURRENT_CFG       = RegisterDef(101, 1, "Max current [A]")
CP_MIN_CURRENT_CFG       = RegisterDef(102, 1, "Min current [A]")
CP_RCM_CONFIGURED        = RegisterDef(103, 1, "RCM configured: 0=no, 1=yes")
CP_TEMP_LOWER_THR        = RegisterDef(104, 1, "Temperature lower threshold [°C]")
CP_TEMP_UPPER_THR        = RegisterDef(105, 1, "Temperature upper threshold [°C]")
CP_CURRENT_DERING_START  = RegisterDef(106, 1, "Current derating start [A]")
CP_CURRENT_DERING_STOP   = RegisterDef(107, 1, "Current derating stop [A]")
CP_TEMP_MONITORING       = RegisterDef(108, 1, "Temperature monitoring type")
CP_ACCEPT_STATUS_D       = RegisterDef(109, 1, "Accept status D: 0=blocked, 1=allow")
CP_PROXIMITY_CFG         = RegisterDef(110, 1, "Proximity pilot configuration")
CP_OVERCURRENT_MON       = RegisterDef(111, 1, "Overcurrent monitoring mode")
CP_ENERGY_METER_TYPE     = RegisterDef(112, 1, "Energy meter type")
CP_UID                   = RegisterDef(113, 3, "CP UID, ASCII (6 chars)")
CP_SERVER_UID            = RegisterDef(116, 3, "Server UID, ASCII")
CP_BUS_POSITION          = RegisterDef(119, 1, "Bus position")
CP_RELEASE_MODE          = RegisterDef(120, 1, "Release mode")
CP_RFID_UID              = RegisterDef(121, 3, "RFID UID placeholder (returns 0)")

CP_CFG_REGISTERS: tuple[RegisterDef, ...] = (
    CP_INTERFACE_CONFIG, CP_MAX_CURRENT_CFG, CP_MIN_CURRENT_CFG,
    CP_RCM_CONFIGURED, CP_TEMP_LOWER_THR, CP_TEMP_UPPER_THR,
    CP_CURRENT_DERING_START, CP_CURRENT_DERING_STOP,
    CP_TEMP_MONITORING, CP_ACCEPT_STATUS_D, CP_PROXIMITY_CFG,
    CP_OVERCURRENT_MON, CP_ENERGY_METER_TYPE,
    CP_UID, CP_SERVER_UID, CP_BUS_POSITION, CP_RELEASE_MODE, CP_RFID_UID,
)

# Status (offsets 232–299)
CP_VOLTAGE_L1        = RegisterDef(232,  2, "Voltage L1 [mV]")
CP_VOLTAGE_L2        = RegisterDef(234,  2, "Voltage L2 [mV]")
CP_VOLTAGE_L3        = RegisterDef(236,  2, "Voltage L3 [mV]")
CP_CURRENT_L1        = RegisterDef(238,  2, "Current L1 [mA]; −1 if phase unknown")
CP_CURRENT_L2        = RegisterDef(240,  2, "Current L2 [mA]")
CP_CURRENT_L3        = RegisterDef(242,  2, "Current L3 [mA]")
CP_ACTIVE_POWER      = RegisterDef(244,  2, "Active power [mW]")
CP_REACTIVE_POWER    = RegisterDef(246,  2, "Reactive power [mVAR] (signed)")
CP_APPARENT_POWER    = RegisterDef(248,  2, "Apparent power [mVA]")
CP_ENERGY_ACTIVE     = RegisterDef(250,  4, "Lifetime active energy [Wh]")
CP_ENERGY_REACTIVE   = RegisterDef(254,  4, "Lifetime reactive energy [VARh] (signed)")
CP_ENERGY_APPARENT   = RegisterDef(258,  4, "Lifetime apparent energy [VAh]")
CP_SOC_KWH           = RegisterDef(262,  2, "SOC [kWh] — placeholder (returns 0)")
CP_SOC_PERCENT       = RegisterDef(264,  1, "SOC [%] — placeholder (returns 0)")
CP_EVCC_ID           = RegisterDef(265, 10, "EVCC ID, ASCII (20 chars)")
CP_LAST_RFID         = RegisterDef(275, 10, "Last RFID tag UID, ASCII")
CP_CONNECTION_TIME   = RegisterDef(285,  2, "Connection time [s] (status B/C/D)")
CP_CHARGING_DURATION = RegisterDef(287,  2, "Charging duration [s] (status C/D)")
CP_SESSION_ENERGY    = RegisterDef(289,  4, "Session energy [Wh]")
CP_ERROR_CODE        = RegisterDef(293,  2, "Error bitmask (MSW=293, LSW=294)")
CP_DIGITAL_INPUTS    = RegisterDef(295,  1, "Digital inputs (1 bit per input)")
CP_SETPOINT_PERCENT  = RegisterDef(296,  1, "Current setpoint [%]")
CP_SETPOINT_AMPERE   = RegisterDef(297,  1, "Current setpoint [A]")
CP_CABLE_CAPACITY    = RegisterDef(298,  1, "Cable capacity [A]")
CP_VEHICLE_STATUS    = RegisterDef(299,  1, "IEC 61851-1 vehicle status (2-char ASCII)")

# Control (offsets 300–308)
CP_CHARGING_RELEASE  = RegisterDef(300,  1, "Charging release (R/W)")
CP_MAX_CURRENT       = RegisterDef(301,  1, "Max current (R/W) [A] range 6–80")
CP_DIGITAL_OUTPUTS   = RegisterDef(302,  1, "Digital outputs (R/W, 4 bits per channel)")
CP_LOCKING           = RegisterDef(303,  1, "Connector lock (R/W)")
CP_STATUS_F          = RegisterDef(304,  1, "Status F / availability (R/W)")
CP_FORCE_UNLOCK      = RegisterDef(305,  1, "Force unlock — write 1 (W)")
CP_WATCHDOG_CURRENT  = RegisterDef(306,  1, "Watchdog fallback current (R/W) [A]")
CP_WATCHDOG_TIMER    = RegisterDef(307,  1, "Watchdog timer (R/W) [s]; 65535 = disabled")
CP_RESET_RFID        = RegisterDef(308,  1, "Clear last RFID tag — write > 0 (W)")

CP_STATUS_REGISTERS: tuple[RegisterDef, ...] = (
    CP_VOLTAGE_L1, CP_VOLTAGE_L2, CP_VOLTAGE_L3,
    CP_CURRENT_L1, CP_CURRENT_L2, CP_CURRENT_L3,
    CP_ACTIVE_POWER, CP_REACTIVE_POWER, CP_APPARENT_POWER,
    CP_ENERGY_ACTIVE, CP_ENERGY_REACTIVE, CP_ENERGY_APPARENT,
    CP_SOC_KWH, CP_SOC_PERCENT,
    CP_EVCC_ID, CP_LAST_RFID,
    CP_CONNECTION_TIME, CP_CHARGING_DURATION, CP_SESSION_ENERGY,
    CP_ERROR_CODE, CP_DIGITAL_INPUTS,
    CP_SETPOINT_PERCENT, CP_SETPOINT_AMPERE, CP_CABLE_CAPACITY, CP_VEHICLE_STATUS,
    CP_CHARGING_RELEASE, CP_MAX_CURRENT, CP_DIGITAL_OUTPUTS,
    CP_LOCKING, CP_STATUS_F, CP_FORCE_UNLOCK,
    CP_WATCHDOG_CURRENT, CP_WATCHDOG_TIMER, CP_RESET_RFID,
)

# ---------------------------------------------------------------------------
# Derived read-window constants
# ---------------------------------------------------------------------------

GLOBAL_BASE  = DEVICE_DESIGNATION.address               # 100
GLOBAL_COUNT = sum(r.width for r in GLOBAL_REGISTERS)   # 68

CP_CFG_OFFSET = CP_INTERFACE_CONFIG.address              # 100
CP_CFG_COUNT  = sum(r.width for r in CP_CFG_REGISTERS)  # 24

CP_STATUS_OFFSET = CP_VOLTAGE_L1.address                          # 232
CP_STATUS_COUNT  = sum(r.width for r in CP_STATUS_REGISTERS)     # 77

# Integer addresses for group-level write operations (imported by client.py)
GROUP_AVAILABILITY        = _GROUP_AVAILABILITY_REG.address   # 164
GROUP_RESET               = _GROUP_RESET_REG.address          # 165
GROUP_SYSTEM_RESET        = _GROUP_SYSTEM_RESET_REG.address   # 166
GROUP_DYNAMIC_MAX_CURRENT = _GROUP_DYNAMIC_MAX_REG.address    # 167


def cp_register(charging_point: int, offset: int | RegisterDef) -> int:
    """Absolute Modbus address for a per-charging-point register.

    charging_point: 1-indexed controller number (matches x in xNNN notation).
    offset: register offset as a plain int or a RegisterDef (its .address is used).
    """
    if not 1 <= charging_point <= 12:
        raise ValueError(f"charging_point must be 1–12, got {charging_point}")
    addr = offset.address if isinstance(offset, RegisterDef) else offset
    return charging_point * 1000 + addr
