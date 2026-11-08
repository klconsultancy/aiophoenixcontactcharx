# One update report per component instead of one atomic snapshot

Status: accepted, targeting 2.0.0

Issue #47 planned the 2.0.0 controller as one atomic snapshot: the whole Component tree refreshes in a single `async_update()`, and any Modbus error fails it entirely, as `fetch_data()` does in 1.x. We're replacing that with `modbus_connection`'s `Device`: `CharxController.async_update()` polls named groups (the controller's identity, the Group, and each Charging Point) and returns an `UpdateReport` that lists the groups that refreshed and the ones that failed. Only a lost connection or a timeout raises. A failed group keeps its last values, and the Home Assistant integration makes only that group's entities unavailable.

With the same `async_poll` the library also handles a register the controller refuses (illegal address or function). It reads that group's fields one by one, once, leaves out the fields that are refused (they read `None`, and a warning names each register), and reads the group again in the same update. Reads touch only mapped addresses (`max_gap = 0`), so a controller or firmware that refuses an address the manual doesn't list doesn't fail a whole read.

## Considered options

- **One atomic snapshot (#47's plan)** — rejected. With `Device`, isolating each Charging Point costs no more code than the snapshot does, and a single failing or missing register would otherwise make every entity of the controller unavailable. In python-thermia-genesis, which uses this pattern, an integration without it lost ~400 entities to one refused register (CJNE/pythermiagenesis#8).
- **Isolation per register block instead of per Charging Point** — rejected. A block is an implementation detail of the read plan, and the integration would need to know about it to decide availability. A Charging Point is a domain unit and a device in Home Assistant already.

## Consequences

`async_update()` returns an `UpdateReport` instead of raising on every Modbus error, and callers check `report.failed` for a partial failure. The integration's coordinator holds the report as its data, and each entity is available while its own group is not in `report.failed`. The reference for the pattern is `ThermiaGenesis.async_update()` in python-thermia-genesis.
