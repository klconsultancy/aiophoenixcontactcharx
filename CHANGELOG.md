# Changelog

## [2.0.0-rc.1](https://github.com/klconsultancy/aiophoenixcontactcharx/compare/v1.0.0...v2.0.0-rc.1) (2026-11-08)


### ⚠ BREAKING CHANGES

* `CharxClient` and the 1.x dataclasses are removed. Use `CharxController(unit)` and `async_update()`; values are in V, A, W and kWh; Modbus errors are `modbus_connection`'s exceptions. See the README's *Upgrading from 1.x*.

### Features

* leave out a register the controller refuses instead of failing its part ([#57](https://github.com/klconsultancy/aiophoenixcontactcharx/issues/57)) ([ba1682e](https://github.com/klconsultancy/aiophoenixcontactcharx/commit/ba1682e650b5c3d7900eb549bda70dd2d37c9bb2))
* map the registers as modbus_connection components, with a dump command ([#54](https://github.com/klconsultancy/aiophoenixcontactcharx/issues/54)) ([3c134fe](https://github.com/klconsultancy/aiophoenixcontactcharx/commit/3c134fef7f141d1be4dac5d74d9619ff772b4e47))
* remove the 1.x CharxClient API ([#59](https://github.com/klconsultancy/aiophoenixcontactcharx/issues/59)) ([627820e](https://github.com/klconsultancy/aiophoenixcontactcharx/commit/627820e92c82c5612e9f610017f36f2579b81393))
* write the controls, with function code 16 and a read-back until they land ([#58](https://github.com/klconsultancy/aiophoenixcontactcharx/issues/58)) ([9beb5d1](https://github.com/klconsultancy/aiophoenixcontactcharx/commit/9beb5d1c5bdae0a765cf20346e8f5ca61fc9ff19))
