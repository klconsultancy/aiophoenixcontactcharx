# Expose the Component tree as the public API, not a dataclass snapshot

Status: accepted, targeting 2.0.0

Through 1.x, `fetch_data()` returned `CharxData`/`ChargingPointData` — dataclasses assembled from raw register reads via a separate decode layer. Adopting `modbus_connection.model` (see [[0003-borrowed-modbus-unit]]) means registers are already mapped to typed attributes on `Component` subclasses (`CharxController`, its `Group`, and a `repeating_group` of `ChargingPoint`). We decided to expose that Component tree itself as the public API instead of translating it into a parallel dataclass shape: one field declaration replaces a dataclass field, a decode function, and an assembly step, and it matches how reference libraries (e.g. Sofar's `SofarInverter`) expose their state.

## Consequences

Breaking change for any consumer of the 1.x `CharxData` shape. `haphoenixcontactcharx`'s entity descriptions reference a component and attribute name (via `getattr`) rather than a fixed dataclass field, mirroring `SofarEntityDescription`.
