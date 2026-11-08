# One update report per component instead of one atomic snapshot

Status: accepted, targeting 2.0.0

Issue #47 planned the 2.0.0 controller as one atomic snapshot: the whole Component tree refreshes in a single `async_update()`, and any Modbus error fails it entirely, as `fetch_data()` does in 1.x. We're replacing that with `modbus_connection`'s `Device`: `CharxController.async_update()` polls named groups (the controller's identity, the Group, and each Charging Point) and returns an `UpdateReport` that lists the groups that refreshed and the ones that failed. Only a lost connection or a timeout raises. A failed group keeps its last values, and the Home Assistant integration makes only that group's entities unavailable.

`CharxController.async_update()` also handles a register the controller refuses (illegal address or function). `Device.async_poll()` doesn't: it only records the refusal in `report.failed`, which fails the whole group. So `async_update()` takes each group that failed with a refusal, reads its fields one by one, once, leaves out the fields that are refused (`restrict_fields`: they read `None`, and a warning names each register), and polls those groups again in the same update. Any other error during that search fails only its group, and the next update searches again. Reads touch only mapped addresses (`max_gap = 0`), so a controller or firmware that refuses an address the manual doesn't list doesn't fail a whole read. `ThermiaGenesis.async_update()` in python-thermia-genesis does the same around its `async_poll()`.

## Considered options

- **One atomic snapshot (#47's plan)** — rejected. With `Device`, isolating each Charging Point costs no more code than the snapshot does, and with a snapshot one failing register makes every entity of the controller unavailable. CJNE/pythermiagenesis#8 shows how large that blast radius gets: one register that fell outside the library's declared ranges raised an `IndexError` that failed every update, and ~400 entities stayed unavailable for six hours over a single alarm flag. That was a register-map error, not a refusal by the device, but a snapshot fails the same way for both.
- **Isolation per register block instead of per Charging Point** — rejected. A block is an implementation detail of the read plan, and the integration would need to know about it to decide availability. A Charging Point is a domain unit and a device in Home Assistant already.

## Consequences

`async_update()` returns an `UpdateReport` instead of raising on every Modbus error, and callers check `report.failed` for a partial failure. The integration's coordinator holds the report as its data, and each entity is available while its own group is not in `report.failed`. The reference for the pattern is `ThermiaGenesis.async_update()` in python-thermia-genesis.
