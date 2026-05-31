"""Data models for Phoenix Contact CHARX SEC EV charging controllers."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum, StrEnum


# ---------------------------------------------------------------------------
# Enumerations (values match the Modbus register encoding from the manual)
# ---------------------------------------------------------------------------

class ReleaseMode(IntEnum):
    DASHBOARD = 0
    LOCAL_WHITELIST = 1
    EXTERNAL_CONTROL = 2
    PERMANENT = 3
    OCPP = 4
    MODBUS = 5


class EnergyMeterType(IntEnum):
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
    NOT_REGISTERED = 0
    REGISTERED = 1
    SEARCHING = 2
    DENIED = 3
    UNKNOWN = 4


class ModemSignalQuality(IntEnum):
    UNKNOWN = 0
    INADEQUATE_TO_NONE = 1
    INADEQUATE = 2
    OK = 3
    GOOD = 4
    EXCELLENT = 5


class OvercurrentMonitoring(IntEnum):
    OFF = 0
    PCT120_10S = 1
    EV_ZE_READY = 2


class TempMonitoring(IntEnum):
    INACTIVE = 0
    PT1000 = 1
    PTC = 2


class VehicleStatus(StrEnum):
    """IEC 61851-1 two-character state codes reported by register X299."""
    A1 = "A1"  # Not connected — supply available
    A2 = "A2"  # Not connected — supply not available
    B1 = "B1"  # Connected — supply available
    B2 = "B2"  # Connected — supply not available
    C1 = "C1"  # Charging request — no ventilation required
    C2 = "C2"  # Charging active
    D1 = "D1"  # Charging request with ventilation — no ventilation available
    D2 = "D2"  # Charging active with ventilation
    E0 = "E0"  # Error
    F0 = "F0"  # Not available (status F)
    IN = "IN"  # Initialising


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class DeviceInfo:
    """Global device and group data from registers 100–167."""

    designation: str = ""
    software_version: str = ""
    num_controllers: int = 0
    mac_eth0: str = ""
    mac_eth1: str = ""
    ip_eth0: str = ""
    ip_eth1: str = ""
    modem_registration: ModemRegistration = ModemRegistration.UNKNOWN
    modem_signal_quality: ModemSignalQuality = ModemSignalQuality.UNKNOWN

    # Group-level counts
    num_non_critical_error: int = 0
    num_status_ef: int = 0
    num_status_a: int = 0
    num_status_bcd: int = 0
    num_charging: int = 0

    # Group-level power/current (mW → W, mA → A, see property helpers)
    group_active_power_mw: int = 0
    group_reactive_power_mvar: int = 0
    group_apparent_power_mva: int = 0
    group_current_l1_ma: int | None = None   # None when phase rotation unknown
    group_current_l2_ma: int | None = None
    group_current_l3_ma: int | None = None

    # Group controls
    availability: bool = True
    dynamic_max_current_a: int = 0

    @property
    def group_active_power_w(self) -> float:
        return self.group_active_power_mw / 1000.0

    @property
    def group_reactive_power_var(self) -> float:
        return self.group_reactive_power_mvar / 1000.0

    @property
    def group_apparent_power_va(self) -> float:
        return self.group_apparent_power_mva / 1000.0

    @property
    def group_current_l1_a(self) -> float | None:
        return None if self.group_current_l1_ma is None else self.group_current_l1_ma / 1000.0

    @property
    def group_current_l2_a(self) -> float | None:
        return None if self.group_current_l2_ma is None else self.group_current_l2_ma / 1000.0

    @property
    def group_current_l3_a(self) -> float | None:
        return None if self.group_current_l3_ma is None else self.group_current_l3_ma / 1000.0


@dataclass
class ChargingPointConfig:
    """Configuration data from registers x100–x121."""

    charging_point: int = 1
    interface_config: int = 0          # 0=socket, 1=connector
    max_current_cfg_a: int = 0
    min_current_cfg_a: int = 0
    rcm_configured: bool = False
    temp_lower_thr_c: int = 0
    temp_upper_thr_c: int = 0
    current_derating_start_a: int = 0
    current_derating_stop_a: int = 0
    temp_monitoring: TempMonitoring = TempMonitoring.INACTIVE
    accept_status_d: bool = False
    proximity_cfg: int = 0
    overcurrent_monitoring: OvercurrentMonitoring = OvercurrentMonitoring.OFF
    energy_meter_type: EnergyMeterType = EnergyMeterType.NONE
    uid: str = ""
    server_uid: str = ""
    bus_position: int = 0
    release_mode: ReleaseMode = ReleaseMode.DASHBOARD


@dataclass
class ChargingPointStatus:
    """Status data from registers x232–x299."""

    charging_point: int = 1

    # Electrical measurements (stored as raw mV/mA/mW; use property helpers)
    voltage_l1_mv: int = 0
    voltage_l2_mv: int = 0
    voltage_l3_mv: int = 0
    current_l1_ma: int | None = None   # None when phase rotation unknown
    current_l2_ma: int | None = None
    current_l3_ma: int | None = None
    active_power_mw: int = 0
    reactive_power_mvar: int = 0        # signed
    apparent_power_mva: int = 0

    # Energy counters [Wh / VARh / VAh]
    energy_active_wh: int = 0
    energy_reactive_varh: int = 0       # signed
    energy_apparent_vah: int = 0
    session_energy_wh: int = 0

    # Session metadata
    last_rfid: str = ""
    last_evcc_id: str = ""
    connection_time_s: int = 0
    charging_duration_s: int = 0

    # Fault & state
    error_code: int = 0                 # 32-bit hex bitmask
    digital_inputs: int = 0
    setpoint_percent: int = 0
    setpoint_a: int = 0
    cable_capacity_a: int = 0
    vehicle_status: VehicleStatus = VehicleStatus.A1

    # Derived property helpers
    @property
    def voltage_l1_v(self) -> float:
        return self.voltage_l1_mv / 1000.0

    @property
    def voltage_l2_v(self) -> float:
        return self.voltage_l2_mv / 1000.0

    @property
    def voltage_l3_v(self) -> float:
        return self.voltage_l3_mv / 1000.0

    @property
    def current_l1_a(self) -> float | None:
        return None if self.current_l1_ma is None else self.current_l1_ma / 1000.0

    @property
    def current_l2_a(self) -> float | None:
        return None if self.current_l2_ma is None else self.current_l2_ma / 1000.0

    @property
    def current_l3_a(self) -> float | None:
        return None if self.current_l3_ma is None else self.current_l3_ma / 1000.0

    @property
    def active_power_w(self) -> float:
        return self.active_power_mw / 1000.0

    @property
    def reactive_power_var(self) -> float:
        return self.reactive_power_mvar / 1000.0

    @property
    def apparent_power_va(self) -> float:
        return self.apparent_power_mva / 1000.0

    @property
    def energy_active_kwh(self) -> float:
        return self.energy_active_wh / 1000.0

    @property
    def session_energy_kwh(self) -> float:
        return self.session_energy_wh / 1000.0


@dataclass
class ChargingPointControl:
    """Control register values from x300–x308."""

    charging_point: int = 1
    charging_release: bool = False
    max_current_a: int = 16
    digital_outputs: int = 0
    locking: bool = False
    available: bool = True
    watchdog_current_a: int = 16
    watchdog_timer_s: int = 65535       # 65535 = disabled


@dataclass
class ChargingPointData:
    """Complete snapshot for one charging point."""

    charging_point: int = 1
    config: ChargingPointConfig = field(default_factory=ChargingPointConfig)
    status: ChargingPointStatus = field(default_factory=ChargingPointStatus)
    control: ChargingPointControl = field(default_factory=ChargingPointControl)

    @property
    def is_connected(self) -> bool:
        """True when a vehicle is physically connected (status B/C/D/E/F)."""
        return self.status.vehicle_status not in ("A1", "A2", "IN")

    @property
    def is_charging(self) -> bool:
        """True when energy is actively being transferred (IEC 61851-1 status C2 or D2)."""
        return self.status.vehicle_status in ("C2", "D2")

    @property
    def has_error(self) -> bool:
        """True when the charging point is in a fault state (IEC 61851-1 status E)."""
        return self.status.vehicle_status == "E0"

    @property
    def is_unavailable(self) -> bool:
        """True when the charging point has been taken out of service (IEC 61851-1 status F)."""
        return self.status.vehicle_status == "F0"


@dataclass
class CharxData:
    """Full data snapshot returned by a single coordinator poll."""

    device_info: DeviceInfo = field(default_factory=DeviceInfo)
    charging_points: list[ChargingPointData] = field(default_factory=list)
