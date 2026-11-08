# Design

The design of `aiophoenixcontactcharx` 2.0 and the reasons behind it. This is a living
document: when a choice changes, edit the section. Git keeps the history; the ADRs in
[`adr/`](adr/) record the decisions that shaped it.

Domain terms are defined in [`CONTEXT.md`](../CONTEXT.md).

## Scope

- One CHARX SEC-3xxx **Charging Controller** and the Charging Points it hosts, up to 12
  (ADR 0001, 0005). Client/Server Groups of several controllers are out of scope.
- Modbus/TCP only, on port 502 and server address 1 (manual, table B-6).

## Connection

- Built on [`modbus-connection`](https://home-assistant-libs.github.io/modbus-connection/)
  with the `tmodbus` backend, the stack Home Assistant's `modbus` integration uses (ADR
  0003). The library never owns a connection: `CharxController` takes a `ModbusUnit`, and
  the caller (Home Assistant, a script, a test) opens and closes it.
- Home Assistant pins an exact `modbus-connection` version per release, so the library
  sets a low floor (`>=4.12.3`, Home Assistant 2026.10.0's) and no upper bound. CI tests
  the floor and, also weekly, the newest release including pre-releases.

## Register map

- **Source of truth:** Appendix B3 of the manual (UM EN CHARX SEC, Revision 08),
  transcribed in [`protocol/B3-modbus.md`](protocol/B3-modbus.md). Where the controller or
  the manual itself disagrees with it, [`errata.md`](errata.md) records how we read it.
- Hand-written with `modbus_connection.model` field types, in
  `aiophoenixcontactcharx.controller`, as three components:
  - `ControllerInfo` (100-146): designation, software version, the number of Charging
    Controllers, network and modem;
  - `Group` (147-167): the counts of Charging Controllers per status, the group's totals
    and its controls;
  - `ChargingPoint` (x100-x307): configuration, status and controls of one Charging
    Point, declared at the offsets of its x000 block.
- A **consistency test** (`tests/test_register_map.py`) parses the manual's tables and
  checks the map in both directions: every field sits at a documented register with the
  documented width, and every documented register is mapped. The exceptions are the three
  command registers (165 reset, 166 system reset, x308 clear the last RFID UID): they are
  written, never read, and come with the write API.
- Field names follow the manual's meaning without the component's name as a prefix
  (`cp.active_power`, `group.active_power`), and say what the value is rather than how
  the manual words the register (`charging_current_duty_cycle` for x296).

## Encoding

- Measurements are scaled to the units Home Assistant shows: the registers' mV, mA, mW,
  mVAR and mVA become V, A, W, var and VA, and Wh, VARh and VAh become kWh, kvarh and
  kVAh. Each field declares its unit.
- 32- and 64-bit values put the most significant word first. Signed are what the manual
  calls "Signed Integer" (reactive power and reactive energy) and the currents, which use
  -1 as a sentinel; everything else is unsigned.
- A current of -1 ("phase rotation unknown") reads `None`. The manual says so for the
  group's totals; a Charging Point's phase currents read the same way, as no real current
  is -1 mA.
- The lifetime active energy (x250) reads `None` for 0. Right after a reconnect the
  controller can report 0 while its meter starts, and a `total_increasing` sensor would
  take that for a meter reset (haphoenixcontactcharx#38). A meter that is in use never
  reads 0; one that has never counted reads `None` until it does. The session energy
  (x289) reads as it is: it keeps the last session's value until the next one starts.
- The Dynamic Max Current (167) reads `None` for 65535, which a controller without a
  dynamic limit reports.
- Strings are ASCII, two characters per register, null-padded. An IPv4 address takes four
  registers with one octet each (`IPv4OctetsField`; `modbus_connection`'s `IPv4Field`
  packs it into two). A MAC address is `modbus_connection`'s `Eui48Field`, lowercase with
  colons (1.x returned uppercase).
- The vehicle status (x299) is two ASCII characters in one register
  (`VehicleStatusField`). An empty register or a code `VehicleStatus` doesn't know reads
  `None`, the latter with a warning.
- An enum value the manual doesn't list reads `None`, with a warning per value
  (`modbus_connection`'s behaviour). The error code keeps unknown bits: `ErrorCode` is an
  `IntFlag`.

## Reads

- Each component declares the address ranges the manual documents (`register_ranges`),
  so a read never bridges into an undocumented address: a controller or firmware may
  refuse one, which would fail the whole read. Within a range, fields share a read. An
  update takes 3 reads for the controller and the group, and 2 per Charging Point.
- The test of the read ranges checks them against the mapped fields, so a new field
  extends its range and a range never covers an unmapped address.

## Public API

```python
controller = CharxController(unit)
report = await controller.async_update()
controller.device_info.designation
controller.group.active_power
controller.charging_points[0].vehicle_status
```

- `CharxController` is a `modbus_connection` `Device`. The first `async_update()` reads
  register 114 (the number of Charging Controllers) and places one `ChargingPoint` per
  controller at its number times 1000, up to 12. `charging_points` is empty until then.
- `async_update()` reads `device_info`, `group` and each `charging_point_N` on its own
  and returns the `UpdateReport` of `Device.async_poll` (ADR 0006): a part whose read
  fails is in `report.failed` and keeps its last values. It raises
  `ModbusConnectionError` when the link is down, and `ModbusTimeoutError` when nothing
  has answered yet.
- A register the controller refuses (illegal data address or illegal function: Modbus
  exception code 2 or 1) doesn't take its part down. On such a refusal `async_update()`
  reads each field of that part on its own, once, leaves out the fields the controller
  refuses (`restrict_fields`: they read `None`, with a warning naming the register and
  the field, or one warning if it refuses the whole part), and reads the part again in
  the same update. Its read ranges split around the left-out registers, so later updates
  don't touch them. Any other error still fails the part; one during the search fails
  only the part too, and the next update searches again. A lost connection raises.
  `Device.async_poll()` itself only records a refusal; this search is the library's, as
  in python-thermia-genesis.
- `ChargingPoint` derives `is_connected`, `is_charging`, `has_error`, `is_unavailable` and
  `watchdog_enabled` from its fields.

## Dump CLI

- `aiophoenixcontactcharx dump <host> [--port 502] [-o file.json]` reads every mapped
  register and writes one JSON object: `registers` (the raw holding registers by
  address, for test fixtures), `values` (decoded per part; an enum as its name, a flag as
  the names of its members, an address as text) and `failed`. It never writes to the
  controller.
- A part whose read fails is left out and listed under `failed`; the JSON is still
  written and the exit status is 1. The dump doesn't leave out refused registers: a bug
  report needs to show the refusal. A lost connection or a timeout ends the command with
  status 1 and no JSON.

## Tests

- `tests/fixtures/sec3xxx-1.7.3.json` is an anonymized dump of a real controller
  (firmware 1.7.3, one Charging Point, no vehicle). `tests/test_real_controller.py`
  decodes it, and `tests/test_end_to_end.py` serves it back over Modbus/TCP and checks
  that the dump command reads exactly the same registers.
- `tests/fixtures/synthetic-sec3100.json` is hand-built for what the real dump doesn't
  show: two Charging Points, a vehicle charging, an unknown phase rotation and an error.
- The tests load the fixtures into `modbus_connection`'s mock unit;
  `tests/test_end_to_end.py` replays them through an in-process tmodbus server.
- Anonymize a dump before it becomes a fixture: the device part of the MAC addresses,
  the IP addresses, the controller UIDs (x113, x116, x121), the last RFID UID (x275) and
  the EVCC ID (x265).
