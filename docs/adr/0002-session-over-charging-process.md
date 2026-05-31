# "Session" preferred over the manual's "Charging Process"

The Phoenix Contact manual consistently uses "Charging Process" for the period from vehicle connection to disconnection. This library uses "Session" instead (e.g. `session_energy_wh`, `session_energy_kwh`) to align with OCPP vocabulary — where a charging event is a "transaction/session" — and with Home Assistant integration conventions. A reader coming from OCPP or HA will recognise "Session" immediately; "Charging Process" would cause a terminology mismatch between the library and its primary consumers.
