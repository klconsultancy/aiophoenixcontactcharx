# aiophoenixcontactcharx

Async Python library for **Phoenix Contact CHARX SEC** EV AC charging controllers (firmware 1.9.0+).

Communicates over **Modbus/TCP** (port 502). Supports the full CHARX SEC-3xxx family (SEC-3000, SEC-3050, SEC-3100, SEC-3150) with up to 12 charging points per controller group.

## Installation

```bash
pip install aiophoenixcontactcharx
```

Requires Python 3.11+ and [`pymodbus`](https://pymodbus.readthedocs.io/) ≥ 3.6.

## Development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/
```

## Quick start

```python
import asyncio
from aiophoenixcontactcharx import CharxClient

async def main():
    async with CharxClient("192.168.1.100") as client:
        data = await client.fetch_data(num_charging_points=1)

        info = data.device_info
        print(f"Device: {info.designation} — SW {info.software_version}")
        print(f"IP ETH0: {info.ip_eth0}")
        print(f"Group power: {info.group_active_power_w:.1f} W")

        cp = data.charging_points[0]
        print(f"CP1 status: {cp.status.vehicle_status}")
        print(f"CP1 power:  {cp.status.active_power_w:.1f} W")
        print(f"CP1 energy: {cp.status.energy_active_kwh:.3f} kWh")

asyncio.run(main())
```

## Writing control values

```python
async with CharxClient("192.168.1.100") as client:
    # Charging point must be in Modbus release mode (configured in WBM)
    await client.set_charging_release(charging_point=1, enabled=True)
    await client.set_max_current(charging_point=1, current_a=11)
    await client.set_availability(charging_point=1, available=True)

    # Load management
    await client.set_dynamic_max_current(current_a=32)
```

## Register map

See `aiophoenixcontactcharx/registers.py` for all addresses. Full documentation is in the Phoenix Contact manual *UM EN CHARX SEC, Revision 08*, Appendix B3 (p. 167–174).

## Modbus prerequisites

Before the client can read or write data:

1. Enable the Modbus server in WBM → System Control → Status.
2. Open TCP port 502 in WBM → Network → Port Sharing.
3. Set the charging point release mode to **Modbus** (WBM → Charging Stations → Charge Point → Configuration → Release Mode) if you want to use `set_charging_release()` or `set_availability()`.

## Supported CHARX models

| Model | Modbus/TCP |
|---|---|
| CHARX SEC-3000 | ✓ |
| CHARX SEC-3050 | ✓ |
| CHARX SEC-3100 | ✓ |
| CHARX SEC-3150 | ✓ |

The CHARX SEC-1000 has no Ethernet and must be attached to a SEC-3xxx as a backplane extension. Its data is accessible via the SEC-3xxx Modbus interface at the corresponding charging point registers.

## License

MIT
