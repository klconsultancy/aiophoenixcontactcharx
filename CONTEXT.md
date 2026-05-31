# aiophoenixcontactcharx

Async Python library for reading and controlling Phoenix Contact CHARX SEC EV AC charging hardware over Modbus/TCP. Primary consumer is Home Assistant.

## Language

### Hardware

**Charging Controller**:
A physical CHARX SEC unit (SEC-3xxx or SEC-1000) that manages exactly one Charging Point. The SEC-3xxx exposes a Modbus/TCP endpoint; SEC-1000 units attach to it via the backplane bus and are accessible through the SEC-3xxx's IP address.
_Avoid_: controller, charger, charging station

**Charging Point**:
The physical EV socket/outlet managed by one Charging Controller. Up to 12 Charging Points are addressable through a single SEC-3xxx.
_Avoid_: charger, EVSE, outlet ("Charge Point" appears only in WBM breadcrumb navigation — use "Charging Point" in code and docs)

### Data

**Snapshot**:
A complete point-in-time read of all data from one Charging Controller — device-level info plus one record per Charging Point. The Home Assistant coordinator polls for a new Snapshot on each update interval.
_Avoid_: poll result, data, update

### Authorization

**Release Mode**:
A per-Charging-Point configuration (set in WBM) that determines what mechanism authorizes charging to start — e.g. OCPP, local whitelist, or Modbus. Must be set to Modbus for this library's control writes to take effect.
_Avoid_: authorization mode, control mode

**Charging Release**:
The per-session authorization signal for one Charging Point. When enabled in Modbus Release Mode, the controller permits a connected vehicle to charge. Automatically withdrawn if an out-of-range current limit is written or the Watchdog expires. Distinct from Availability — Charging Release controls whether a connected vehicle may charge; Availability controls whether the Charging Point is in service at all.
_Avoid_: enable charging, start charging, charge enable

**Availability**:
Whether a Charging Point is in service. Setting a Charging Point unavailable puts it into IEC 61851-1 status F ("not available"), aborts any active Session, and shows it as "Error" in WBM. Distinct from Charging Release, which operates at the session level.
_Avoid_: enabled, active, online

### Charging lifecycle

**Vehicle Status**:
The IEC 61851-1 two-character state code reported by a Charging Point (e.g. `"A1"` = not connected, `"C2"` = actively charging, `"F0"` = unavailable). The library exposes the raw code alongside derived boolean properties.
_Avoid_: charge state, status code, EV state

**Session**:
The period from when a vehicle connects to when it disconnects. Tracks energy delivered, charging duration, and connection time. Deliberate divergence from the manual's "Charging Process" — "Session" aligns with OCPP vocabulary and Home Assistant conventions.
_Avoid_: charging process, transaction, charge event

**Charging Duration**:
Time a vehicle has spent in active charging status (IEC 61851-1 state C or D) within the current Session. Distinct from Connection Time, which counts all time since the vehicle plugged in.
_Avoid_: session duration, active time

### Group controls

**Load Management**:
The group-level feature that caps total current across all Charging Points via a single configurable maximum. Applies to the whole group, not individual Charging Points.
_Avoid_: current limiting, power management, smart charging

**Watchdog**:
A safety mechanism that automatically withdraws the Charging Release if the Modbus client fails to write a new value within a configured interval. Falls back to a pre-configured safe current on expiry.
_Avoid_: heartbeat, keepalive, safety timer
