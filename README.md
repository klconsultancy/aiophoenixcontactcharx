# aiophoenixcontactcharx

Async Python library for **Phoenix Contact CHARX SEC** EV AC charging controllers over
**Modbus/TCP**: one SEC-3xxx and the Charging Points it hosts, its own and up to 11
SEC-1000 behind it.

It is built on [`modbus-connection`](https://home-assistant-libs.github.io/modbus-connection/),
the stack Home Assistant's `modbus` integration uses. The library never owns a
connection: you hand it a `ModbusUnit`. Its primary consumer is the Home Assistant
integration [haphoenixcontactcharx](https://github.com/klconsultancy/haphoenixcontactcharx).

## Installation

```bash
pip install "aiophoenixcontactcharx[tmodbus]"
```

Requires Python 3.12+. The `tmodbus` extra installs the Modbus backend; leave it out when
the caller brings its own, as Home Assistant does.

## Reading

```python
import asyncio

from modbus_connection import ModbusTcpParams
from modbus_connection.tmodbus import ModbusConnection

from aiophoenixcontactcharx import CharxController


async def main() -> None:
    connection = ModbusConnection(ModbusTcpParams(host="192.168.1.100", port=502))
    await connection.connect()
    try:
        controller = CharxController(connection.for_unit(1))
        report = await controller.async_update()
        if report.failed:
            print("not refreshed:", ", ".join(report.failed))

        print(controller.device_info.software_version)  # "1.7.3"
        print(controller.group.active_power)  # W
        for cp in controller.charging_points:
            print(cp.number, cp.vehicle_status, cp.active_energy)  # kWh
    finally:
        await connection.close()


asyncio.run(main())
```

- The first `async_update()` reads how many Charging Controllers the system has
  (register 114) and places a `ChargingPoint` for each, up to 12.
- Every update reads `device_info`, `group` and each Charging Point on its own, and
  returns an `UpdateReport`. A part that fails is in `report.failed` and keeps its last
  values; only a lost connection or a timeout raises.
- A register the controller refuses is left out (it reads `None`, with a warning), and
  tried again an hour later.
- Values are typed and in V, A, W and kWh. A value the controller can't give reads
  `None`: an unknown phase rotation, a lifetime energy of 0 right after a reconnect, no
  dynamic limit set.

## Controlling

```python
cp = controller.charging_points[0]
await cp.set_max_current(16)  # 6-80 A
await cp.set_charging_release(True)  # needs release mode Modbus
await controller.group.set_dynamic_max_current(20)  # load management, any release mode
await controller.group.set_dynamic_max_current(None)  # clear the limit
```

- A write uses Modbus function code 16 and returns once the controller reports the new
  value, which takes up to about 2 s. After 5 s it raises `CharxWriteNotConfirmedError`.
- A value out of range raises `ValueError` before anything is written.
- The charging release and the availability need the Charging Point's release mode set
  to **Modbus** (WBM: Charging Stations, Charge Point, Configuration, Release Mode). In any
  other mode they raise `CharxReleaseModeError`.
- The Dynamic Max Current works in every release mode. So with an OCPP backend that
  authorizes the sessions, it is the way to limit the charging current.

## Modbus prerequisites

1. Enable the Modbus server (WBM: System Control, Status).
2. Open TCP port 502 (WBM: Network, Port Sharing).
3. For the charging release and the availability, set the release mode to Modbus (see
   above).

## Dump

```bash
aiophoenixcontactcharx dump 192.168.1.100 -o charx.json
```

This reads every mapped register and writes the raw registers and the decoded values as
JSON, for bug reports and test fixtures. It never writes to the controller. Anonymize a
dump before sharing it: it holds the MAC and IP addresses, the controller's UIDs and the
last RFID UID.

## Documentation

- [docs/design.md](docs/design.md): the register map, the encoding, the reads, the
  writes and the public API.
- [docs/errata.md](docs/errata.md): where the manual is wrong or unclear, and what a real
  controller does.
- [docs/protocol/B3-modbus.md](docs/protocol/B3-modbus.md): the register tables of the
  manual (UM EN CHARX SEC, Revision 08, Appendix B3).
- [docs/adr/](docs/adr/): the decisions behind 2.0.

## Upgrading from 1.x

2.0 replaces `CharxClient` and its dataclasses (`CharxData`, `ChargingPointData`,
`DeviceInfo`) with `CharxController` on a borrowed `ModbusUnit`:

- `fetch_data()` becomes `async_update()`, which returns an `UpdateReport` instead of
  raising on every Modbus error.
- The parts move, and most fields are renamed: they drop their unit suffix, as values are
  now in V, A, W and kWh rather than mV, mA, mW and Wh, and follow the manual's meaning.
- A MAC address is lowercase.
- `DigitalOutputMode` and `pack_digital_outputs` become `DigitalOutputState` and
  `cp.set_digital_outputs(...)`, which follow the manual's coding (1.x's was wrong).
- The `CharxConnectionError` family becomes `modbus_connection`'s exceptions.
- Python 3.12 is the minimum, and `pymodbus` is no longer a dependency.

**Reading** (`cp` is a Charging Point: `data.charging_points[i]` in 1.x,
`controller.charging_points[i]` in 2.0)

| 1.x | 2.0 |
|---|---|
| `data.device_info.designation`, `software_version`, `mac_eth0`, `ip_eth0`, `modem_registration` | `controller.device_info.` the same name |
| `data.device_info.num_controllers` | `controller.device_info.charging_controllers` |
| `data.device_info.subnet_eth0` | `controller.device_info.subnet_mask_eth0` |
| `data.device_info.group_active_power_w` (`_mw`), `group_reactive_power_var`, `group_apparent_power_va` | `controller.group.active_power`, `reactive_power`, `apparent_power` |
| `data.device_info.group_current_l1_a` (`_ma`) | `controller.group.current_l1` |
| `data.device_info.num_charging`, `num_status_a`, `num_status_bcd`, `num_status_ef`, `num_non_critical_error` | `controller.group.charging`, `status_a`, `status_b_c_or_d`, `status_e_or_f`, `non_critical_errors` |
| `data.device_info.availability` | `controller.group.available` |
| `data.device_info.dynamic_max_current_a` | `controller.group.dynamic_max_current` (`None` while no limit is set) |
| `cp.config.interface_config` (int) | `cp.interface` (`ChargingInterface`) |
| `cp.config.max_current_cfg_a`, `min_current_cfg_a` | `cp.max_current_config`, `min_current_config` |
| `cp.config.temp_lower_thr_c`, `temp_upper_thr_c` | `cp.derating_start_temperature`, `derating_stop_temperature` |
| `cp.config.current_derating_start_a`, `current_derating_stop_a` | `cp.derating_start_current`, `derating_stop_current` |
| `cp.config.temp_monitoring`, `proximity_cfg` | `cp.temperature_monitoring`, `proximity_configuration` |
| `cp.config.rcm_configured`, `accept_status_d`, `overcurrent_monitoring`, `energy_meter_type`, `uid`, `server_uid`, `bus_position`, `release_mode` | `cp.` the same name |
| `cp.status.voltage_l1_v` (`_mv`), `current_l1_a` (`_ma`) | `cp.voltage_l1`, `cp.current_l1` |
| `cp.status.active_power_w` (`_mw`), `reactive_power_var`, `apparent_power_va` | `cp.active_power`, `reactive_power`, `apparent_power` |
| `cp.status.energy_active_kwh` (`_wh`), `energy_reactive_varh`, `energy_apparent_vah` | `cp.active_energy`, `reactive_energy`, `apparent_energy` (kWh, kvarh, kVAh) |
| `cp.status.session_energy_kwh` (`_wh`) | `cp.session_energy` |
| `cp.status.connection_time_s`, `charging_duration_s` | `cp.connection_time`, `charging_duration` |
| `cp.status.last_rfid`, `last_evcc_id` | `cp.rfid_uid`, `evcc_id` |
| `cp.status.setpoint_a`, `setpoint_percent`, `cable_capacity_a` | `cp.charging_current`, `charging_current_duty_cycle`, `cable_capacity` |
| `cp.status.error_code`, `digital_inputs`, `vehicle_status` | `cp.` the same name |
| `cp.control.charging_release`, `available`, `digital_outputs` | `cp.` the same name |
| `cp.control.max_current_a`, `locking`, `force_unlock_pending` | `cp.max_current`, `locked`, `force_unlock` |
| `cp.control.watchdog_current_a`, `watchdog_timer_s` | `cp.watchdog_current`, `watchdog_timer` |
| `cp.is_connected`, `is_charging`, `has_error`, `is_unavailable` | `cp.` the same name |

**Controlling**

| 1.x | 2.0 |
|---|---|
| `client.set_charging_release(n, enabled)` | `cp.set_charging_release(enabled)` |
| `client.set_max_current(n, current_a)` | `cp.set_max_current(amps)` |
| `client.set_availability(n, available)` | `cp.set_available(available)` |
| `client.set_locking(n, locked)` | `cp.set_locked(locked)` |
| `client.set_digital_outputs(n, value)` | `cp.set_digital_outputs(state_1, state_2, state_3, state_4)` |
| `client.set_watchdog(...)` | `cp.set_watchdog_current(amps)`, `cp.set_watchdog_timer(seconds)` (`None` disables) |
| `client.force_unlock(n)` | `cp.enforce_unlocking()` |
| `client.reset_last_rfid(n)` | `cp.clear_last_rfid()` |
| `client.set_group_availability(available)` | `controller.group.set_available(available)` |
| `client.set_dynamic_max_current(current_a)` | `controller.group.set_dynamic_max_current(amps)` (`None` clears) |

## Development

```bash
uv sync
uv run pytest
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the lint and type checks.

## License

MIT
