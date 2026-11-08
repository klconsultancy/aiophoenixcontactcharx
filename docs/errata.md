# Errata

Where the manual (UM EN CHARX SEC, Revision 08, Appendix B3; transcribed in
[`protocol/B3-modbus.md`](protocol/B3-modbus.md)) contradicts itself, is unclear, or
differs from what a controller does, and how the map handles it. A dump of a real
controller decides: `tests/fixtures/sec3xxx-1.7.3.json` (firmware 1.7.3, one Charging
Point in OCPP release mode, no vehicle). Each entry says whether that dump confirms it.

## x302: the coding of the digital outputs

The manual codes each output in 4 bits as 0 undefined, 1 floating, 2 permanent 0 V
("low"), 3 flashing 0 V, 4 pulsating 0 V, 5 permanent 12 V ("high") and 6 flashing 12 V,
and its example (`0001 0001 0010 0011` = 1 1 2 3) agrees. The 1.x `DigitalOutputMode`
(0 floating, 1 low, 2 high, 3 flashing, 4 pulsatile) doesn't. `DigitalOutputState`
follows the manual.

**Confirmed by the dump:** the four outputs of an idle controller read `0x1111`, state 1
each, which is floating in the manual's coding (the state of an output nothing drives)
and low in 1.x's.

## 167: writable in OCPP release mode, applied late, echoed wrong

The manual gives the Dynamic Max Current as R/W without a condition. A test on the dumped
controller (OCPP release mode, no vehicle) wrote 16 and restored 65535 with function
code 06 (write single register):

- **The write works in OCPP release mode.** Load management can limit the current
  while an OCPP backend authorizes the sessions.
- **The controller applies it within about 2 s.** A read straight after the write
  still returns the old value.
- **Its response echoes the old value, not the written one.** Modbus requires a function
  code 06 response to echo the request, so `modbus_connection` raises
  `ModbusProtocolError` ("Expected response to match request") although the write
  lands.

The write API therefore writes with function code 16 (write multiple registers,
`force_fc16=True`), whose response echoes only the address and the count, and reads the
register back until the value has landed. Whether the controller answers function code
16 correctly is not yet tested.

## x300, x303, x304: writable only when configured

The manual makes charging release (x300) and availability (x304) writable only when the
Charging Point is set to release via Modbus, which x120 shows: the library refuses those
writes in any other release mode. It makes locking (x303) writable only when the locking
is set to external control, and enforcing unlocking (x305) only when it isn't; no
register shows that setting, so the library writes them unchecked. The maximum current
(x301), the watchdog (x306, x307) and the Dynamic Max Current (167) have no condition.
Writing x300, x303, x304 or x305 is not tested: the dumped controller has to stay in OCPP
release mode for its operator.

## 114: Charging Controllers, read as Charging Points

Register 114 counts the Charging Controllers of the system, on the backplane bus and over
Ethernet. The map places one Charging Point per Charging Controller, as 1.x did: a
SEC-3xxx and each SEC-1000 behind it host one Charging Point each. Over Ethernet, clients
of a Client/Server Group count too, which is out of scope (ADR 0001, 0005).

## 100: the device designation is the controller's name

The manual calls register 100 the "device designation". The dump reads `ev3000`, not a
model name such as "CHARX SEC-3100"; it is probably the name set for the controller in
the WBM, which is unverified. 1.x and the Home Assistant integration show it as the
device's model.

## 167: 65535 while no dynamic limit is set

The manual gives the Dynamic Max Current in A. The dump reads 65535, which no charging
current is: the controller has no load management limit set. The map reads 65535 as
`None`.

## x121: the RFID reader's UID is the controller's UID

The manual calls x121 a placeholder that reads 0. The dump reads the same 6 characters
as x113, the controller's UID.

## x301: 0 outside Modbus release mode

x301 (the maximum charging current, 6-80 A) reads 0 on the dumped controller, whose
release mode is OCPP, although the manual's range is 6-80. Probably no limit has been set
over Modbus, which is unverified. The map reads it as it is.

## x305: reads 1 while idle

x305 ("enforce unlocking": 1 performs it) reads 1 on the dumped, idle controller, with
nothing locked (x303 reads 0). What a read of 1 means is unclear; the map reads it as it
is, and it is not used for any state.

## x262: SOC in kWh or Wh

The meaning says "SOC in kWh", the coding "Integer [Wh]". The register is a placeholder
that reads 0; the map follows the coding (Wh).

## x308: a unit of A

The coding of "reset the last RFID tag" says "Integer [A]", but the register is a
command: any value above 0 clears x275. It isn't read (see the design's command
registers).

## x289: the session energy stays after the session

The manual calls x289 the energy of the current charging process. With no vehicle
connected, the dump reads 42.952 kWh: the value of the last session stays until the next
one starts.

## 162: in German

The coding of the total current on L3 is in German ("-1, wenn Phasendrehung =
unbekannt"); it means the same as 158 and 160: -1 if the phase rotation is unknown.

## -1 for a Charging Point's phase currents

The manual documents -1 ("phase rotation unknown") for the group's total currents only.
A Charging Point's phase currents (x238-x243) read -1 as `None` too, as 1.x did: no real
current is -1 mA, so the sentinel can't hide a reading. The dump has a known phase
rotation (every total and phase current reads 0), so it doesn't show whether a
controller sends -1 there.

## Holding or input registers

Table B-6 says holding (FC03) and input (FC04) registers return the same values. The map
reads holding registers.
