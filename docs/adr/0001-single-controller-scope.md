# Scope limited to a single Charging Controller

The CHARX SEC-3xxx hardware supports client/server groups of up to 48 charging controllers reachable through a single IP address, but this library is intentionally scoped to one SEC-3xxx (plus any SEC-1000 backplane extensions it hosts). A single `CharxClient` instance represents exactly one controller. Multi-controller group support was deferred to keep the API surface and polling logic simple; if needed later it would require a new coordinator-level abstraction above `CharxClient`.
