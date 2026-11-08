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
- `data.device_info` becomes `controller.device_info` (identity and network) and
  `controller.group` (counts, totals, controls). `cp.status.x`, `cp.config.x` and
  `cp.control.x` become `cp.x`.
- Values are in V, A, W and kWh instead of mV, mA, mW and Wh.
- A MAC address is lowercase.
- `DigitalOutputMode` and `pack_digital_outputs` become `DigitalOutputState` and
  `cp.set_digital_outputs(...)`, which follow the manual's coding (1.x's was wrong).
- The `CharxConnectionError` family becomes `modbus_connection`'s exceptions.
- Python 3.12 is the minimum, and `pymodbus` is no longer a dependency.

## Development

```bash
uv sync
uv run pytest
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the lint and type checks.

## License

MIT
