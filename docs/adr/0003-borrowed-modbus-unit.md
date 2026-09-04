# Borrow a ModbusUnit instead of owning the connection

Status: accepted, targeting 2.0.0

`CharxClient` has always opened and reconnected its own `AsyncModbusTcpClient`. Home Assistant's 2026.9 release introduced a standalone `modbus_connection` library plus a shared-connection pattern (`async_get_unit`/`async_get_temporary_unit`) that HA's own `modbus` integration now hands out; connection lifecycle, reconnects, and backend choice all move out of individual device libraries. We're rebuilding `aiophoenixcontactcharx` around a borrowed `ModbusUnit` from `modbus_connection` rather than owning the socket, so we stop re-implementing infrastructure the platform now provides and stay aligned with the pattern new core integrations (Sofar, Flexit) already use.

## Considered options

- **Keep owning the connection directly** — rejected: duplicates reconnect/lifecycle logic HA now provides centrally, and diverges from where reference integrations are heading.
- **`modbus_connection[pymodbus]` backend** — rejected for now, in favor of `tmodbus`: `tmodbus` is the direction HA's 2026.9 blog frames as the modern path, and `modbus_connection` abstracts the backend behind one interface (its own test suite cross-validates both), so swapping later is a low-cost, isolated change if `tmodbus` doesn't pan out.

## Consequences

`aiophoenixcontactcharx` gains a runtime dependency on `modbus_connection` (itself HA-agnostic) and drops the direct `pymodbus` dependency. `haphoenixcontactcharx`'s `manifest.json` gains `"dependencies": ["modbus"]`.
