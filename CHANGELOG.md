# Changelog

## [2.0.0](https://github.com/klconsultancy/aiophoenixcontactcharx/compare/v1.0.0...v2.0.0) (2026-11-10)

Upgrading from 1.x: these notes cover everything since 1.0.0, including 2.0.0-rc.1. The README's *Upgrading from 1.x* maps every 1.x call and field to 2.0.

### ⚠ BREAKING CHANGES

* `CharxClient` and the 1.x dataclasses are removed. Use `CharxController(unit)` and `async_update()`; values are in V, A, W and kWh; Modbus errors are `modbus_connection`'s exceptions. See the README's *Upgrading from 1.x*.
* The library runs on a `modbus_connection` `ModbusUnit` the caller provides (`modbus-connection[tmodbus]`, as Home Assistant 2026.10 uses) instead of its own pymodbus client.
* Requires Python 3.12 or later.

### Features

* map the registers as modbus_connection components, with a dump command ([#54](https://github.com/klconsultancy/aiophoenixcontactcharx/issues/54)) ([3c134fe](https://github.com/klconsultancy/aiophoenixcontactcharx/commit/3c134fef7f141d1be4dac5d74d9619ff772b4e47))
  * `async_update()` returns an update report per part (identity, Group, every Charging Point): one part that fails no longer fails the others. Only a lost connection or a timeout raises.
  * `aiophoenixcontactcharx dump <host>` writes the raw registers and the decoded values as JSON, and never writes to the controller.
* leave out a register the controller refuses instead of failing its part ([#57](https://github.com/klconsultancy/aiophoenixcontactcharx/issues/57)) ([ba1682e](https://github.com/klconsultancy/aiophoenixcontactcharx/commit/ba1682e650b5c3d7900eb549bda70dd2d37c9bb2)); it is retried hourly
* write the controls, with function code 16 and a read-back until they land ([#58](https://github.com/klconsultancy/aiophoenixcontactcharx/issues/58)) ([9beb5d1](https://github.com/klconsultancy/aiophoenixcontactcharx/commit/9beb5d1c5bdae0a765cf20346e8f5ca61fc9ff19))
  * values are validated before anything goes on the wire; a write the release mode doesn't allow raises `CharxReleaseModeError` instead of doing nothing.
  * `Group.set_dynamic_max_current(None)` clears the limit.
* remove the 1.x CharxClient API ([#59](https://github.com/klconsultancy/aiophoenixcontactcharx/issues/59)) ([627820e](https://github.com/klconsultancy/aiophoenixcontactcharx/commit/627820e92c82c5612e9f610017f36f2579b81393))

### Bug Fixes

* the register map follows the controller where the manual is wrong or unclear, for example the coding of the digital outputs (x302), 65535 for "no dynamic limit" (167) and 0 for the max current outside release mode Modbus (x301); `docs/errata.md` lists them all

Tested on a real CHARX SEC-3050 (firmware 1.7.3, release mode OCPP) through haphoenixcontactcharx 2.0.0-rc.1 since 2026-11-09.

## [2.0.0-rc.1](https://github.com/klconsultancy/aiophoenixcontactcharx/compare/v1.0.0...v2.0.0-rc.1) (2026-11-08)


### ⚠ BREAKING CHANGES

* `CharxClient` and the 1.x dataclasses are removed. Use `CharxController(unit)` and `async_update()`; values are in V, A, W and kWh; Modbus errors are `modbus_connection`'s exceptions. See the README's *Upgrading from 1.x*.

### Features

* leave out a register the controller refuses instead of failing its part ([#57](https://github.com/klconsultancy/aiophoenixcontactcharx/issues/57)) ([ba1682e](https://github.com/klconsultancy/aiophoenixcontactcharx/commit/ba1682e650b5c3d7900eb549bda70dd2d37c9bb2))
* map the registers as modbus_connection components, with a dump command ([#54](https://github.com/klconsultancy/aiophoenixcontactcharx/issues/54)) ([3c134fe](https://github.com/klconsultancy/aiophoenixcontactcharx/commit/3c134fef7f141d1be4dac5d74d9619ff772b4e47))
* remove the 1.x CharxClient API ([#59](https://github.com/klconsultancy/aiophoenixcontactcharx/issues/59)) ([627820e](https://github.com/klconsultancy/aiophoenixcontactcharx/commit/627820e92c82c5612e9f610017f36f2579b81393))
* write the controls, with function code 16 and a read-back until they land ([#58](https://github.com/klconsultancy/aiophoenixcontactcharx/issues/58)) ([9beb5d1](https://github.com/klconsultancy/aiophoenixcontactcharx/commit/9beb5d1c5bdae0a765cf20346e8f5ca61fc9ff19))
