# Client/Server Group support is a register-range problem, not a connection-sharing problem

Status: amends [[0001-single-controller-scope]] (scope decision unchanged, rationale corrected)

[[0001-single-controller-scope]] deferred multi-controller Client/Server Group support, reasoning it would need "a new coordinator-level abstraction above `CharxClient`" — written when the natural mental model was one connection per controller. The CHARX manual (§2.5.8, "Modbus/TCP") clarifies that a Client/Server Group is reached over a **single** Modbus/TCP connection at the fixed server address (unit ID 1, always); the group only extends the existing per-position `x000`-`x999` register addressing scheme (already used for backplane charging points within one controller) to cover every controller's charging points, not multiple unit IDs over a shared connection.

We're recording this so a future reader doesn't assume the 2.0 architecture migration ([[0003-borrowed-modbus-unit]], which borrows one `ModbusUnit` per config entry) already solves, or is a prerequisite for, Client/Server Group support — it doesn't touch this problem at all. Group support stays out of scope per ADR 0001; if and when it's tackled, it is purely a register-map and polling-range extension inside `aiophoenixcontactcharx`, independent of which HA integration architecture reaches the device.
