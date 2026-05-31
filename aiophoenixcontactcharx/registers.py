"""Modbus register addresses for Phoenix Contact CHARX SEC EV charging controllers.

Source: UM EN CHARX SEC, Revision 08 — Appendix B3, p. 167–174.
All addresses are 0-indexed Modbus PDU addresses (as used by pymodbus).
"""

# ---------------------------------------------------------------------------
# Global registers (address range 0–999)
# Applies to the entire group (server + all clients + backplane modules).
# ---------------------------------------------------------------------------

DEVICE_DESIGNATION = 100    # 10 words, ASCII (20 chars)
SOFTWARE_VERSION = 110       # 4 words, ASCII (8 chars)
NUM_CONTROLLERS = 114        # 1 word, integer
MAC_ETH0 = 115               # 3 words, HEX (bytes 0–5)
MAC_ETH1 = 118               # 3 words, HEX
IP_ETH0 = 121                # 4 words, 4× octet integers
IP_ETH1 = 125                # 4 words, 4× octet integers
SUBNET_ETH0 = 129            # 4 words, 4× octet integers
SUBNET_ETH1 = 133            # 4 words, 4× octet integers
GATEWAY_ETH0 = 137           # 4 words, placeholder (returns 0)
GATEWAY_ETH1 = 141           # 4 words, placeholder (returns 0)
MODEM_REGISTRATION = 145     # 1 word
MODEM_SIGNAL_QUALITY = 146   # 1 word
NUM_NON_CRITICAL_ERROR = 147 # 1 word
NUM_STATUS_EF = 148          # 1 word
NUM_STATUS_A = 149           # 1 word
NUM_STATUS_BCD = 150         # 1 word
NUM_CHARGING = 151           # 1 word (active C2 sessions)
GROUP_ACTIVE_POWER = 152     # 2 words, integer [mW]
GROUP_REACTIVE_POWER = 154   # 2 words, signed integer [mVAR]
GROUP_APPARENT_POWER = 156   # 2 words, integer [mVA]
GROUP_CURRENT_L1 = 158       # 2 words, integer [mA]; −1 if phase unknown
GROUP_CURRENT_L2 = 160       # 2 words, integer [mA]
GROUP_CURRENT_L3 = 162       # 2 words, integer [mA]
GROUP_AVAILABILITY = 164     # 1 word, R/(W if configured)
GROUP_RESET = 165            # 1 word, W — restart server only
GROUP_SYSTEM_RESET = 166     # 1 word, W — restart all controllers
GROUP_DYNAMIC_MAX_CURRENT = 167  # 1 word, R/W [A] — load management

# ---------------------------------------------------------------------------
# Per-charging-point register offsets
# Absolute address = charging_point_number × 1000 + offset.
# Default start addresses: CP1 → 1000, CP2 → 2000, … CP12 → 12000.
# ---------------------------------------------------------------------------

# Configuration (offsets 100–123 within the x000 block)
CP_INTERFACE_CONFIG = 100    # 1 word; 0=socket, 1=connector
CP_MAX_CURRENT_CFG = 101     # 1 word [A]
CP_MIN_CURRENT_CFG = 102     # 1 word [A]
CP_RCM_CONFIGURED = 103      # 1 word; 0=no, 1=yes
CP_TEMP_LOWER_THR = 104      # 1 word [°C]
CP_TEMP_UPPER_THR = 105      # 1 word [°C]
CP_CURRENT_DERING_START = 106  # 1 word [A]
CP_CURRENT_DERING_STOP = 107   # 1 word [A]
CP_TEMP_MONITORING = 108     # 1 word; 0=off, 1=Pt1000, 2=PTC
CP_ACCEPT_STATUS_D = 109     # 1 word; 0=blocked, 1=allow
CP_PROXIMITY_CFG = 110       # 1 word; 0=IEC 61851-1
CP_OVERCURRENT_MON = 111     # 1 word; 0=off, 1=120%/10s, 2=EV/ZE Ready
CP_ENERGY_METER_TYPE = 112   # 1 word; see EnergyMeterType
CP_UID = 113                 # 3 words, ASCII (6 chars)
CP_SERVER_UID = 116          # 3 words, ASCII
CP_BUS_POSITION = 119        # 1 word
CP_RELEASE_MODE = 120        # 1 word; see ReleaseMode
CP_RFID_UID = 121            # 3 words, ASCII (placeholder, returns 0)

# Status (offsets 232–299)
CP_VOLTAGE_L1 = 232          # 2 words, uint32 [mV]
CP_VOLTAGE_L2 = 234          # 2 words, uint32 [mV]
CP_VOLTAGE_L3 = 236          # 2 words, uint32 [mV]
CP_CURRENT_L1 = 238          # 2 words, int32 [mA]; −1 if phase unknown
CP_CURRENT_L2 = 240          # 2 words, int32 [mA]
CP_CURRENT_L3 = 242          # 2 words, int32 [mA]
CP_ACTIVE_POWER = 244        # 2 words, uint32 [mW]
CP_REACTIVE_POWER = 246      # 2 words, int32 [mVAR] (signed)
CP_APPARENT_POWER = 248      # 2 words, uint32 [mVA]
CP_ENERGY_ACTIVE = 250       # 4 words, uint64 [Wh]
CP_ENERGY_REACTIVE = 254     # 4 words, int64 [VARh] (signed)
CP_ENERGY_APPARENT = 258     # 4 words, uint64 [VAh]
CP_SOC_KWH = 262             # 2 words, placeholder (returns 0)
CP_SOC_PERCENT = 264         # 1 word, placeholder (returns 0)
CP_EVCC_ID = 265             # 10 words, ASCII (20 chars)
CP_LAST_RFID = 275           # 10 words, ASCII (20 chars)
CP_CONNECTION_TIME = 285     # 2 words, uint32 [s] — time in status B/C/D
CP_CHARGING_DURATION = 287   # 2 words, uint32 [s] — time in C/D, reset B→A
CP_SESSION_ENERGY = 289      # 4 words, uint64 [Wh] — current session
CP_ERROR_CODE = 293          # 2 words, hexadecimal (MSB=293, LSB=294)
CP_DIGITAL_INPUTS = 295      # 1 word, binary (1 bit per input)
CP_SETPOINT_PERCENT = 296    # 1 word [%]
CP_SETPOINT_AMPERE = 297     # 1 word [A]
CP_CABLE_CAPACITY = 298      # 1 word [A]
CP_VEHICLE_STATUS = 299      # 1 word, 2-char ASCII; e.g. 'C2' = 0x4332

# Control (offsets 300–308)
CP_CHARGING_RELEASE = 300    # 1 word, R/W (must be in Modbus release mode)
CP_MAX_CURRENT = 301         # 1 word, R/W [A] range 6–80
CP_DIGITAL_OUTPUTS = 302     # 1 word, R/W (4 bits per output)
CP_LOCKING = 303             # 1 word, R/W (must be configured for external)
CP_STATUS_F = 304            # 1 word, R/W (must be in Modbus release mode)
CP_FORCE_UNLOCK = 305        # 1 word, R/W; write 1 to unlock
CP_WATCHDOG_CURRENT = 306    # 1 word, R/W [A] — current on watchdog expiry
CP_WATCHDOG_TIMER = 307      # 1 word, R/W [s]; 65535 = disabled
CP_RESET_RFID = 308          # 1 word, R/W; write >0 to clear last RFID tag

# Derived read windows ---------------------------------------------------------
# Global: read registers 100–167 → 68 registers
GLOBAL_BASE = 100
GLOBAL_COUNT = 68

# Per-CP config: read x*1000+100 → 24 registers (offsets 100–123)
CP_CFG_OFFSET = 100
CP_CFG_COUNT = 24

# Per-CP status+control: read x*1000+232 → 77 registers (offsets 232–308)
CP_STATUS_OFFSET = 232
CP_STATUS_COUNT = 77  # 308 − 232 + 1


def cp_register(charging_point: int, offset: int) -> int:
    """Absolute Modbus address for a per-charging-point register.

    charging_point: 1-indexed controller number (matches x in xNNN notation).
    offset: the per-CP register offset (e.g. CP_VEHICLE_STATUS = 299).
    """
    if not 1 <= charging_point <= 48:
        raise ValueError(f"charging_point must be 1–48, got {charging_point}")
    return charging_point * 1000 + offset
