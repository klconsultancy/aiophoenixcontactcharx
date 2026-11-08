# Errata

Where the manual (UM EN CHARX SEC, Revision 08, Appendix B3; transcribed in
[`protocol/B3-modbus.md`](protocol/B3-modbus.md)) contradicts itself, is unclear, or
differs from what a controller does, and how the map handles it. A dump of a real
controller decides; until there is one, each entry says what is unverified.

## x302: the coding of the digital outputs

The manual codes each output in 4 bits as 0 undefined, 1 floating, 2 permanent 0 V
("low"), 3 flashing 0 V, 4 pulsating 0 V, 5 permanent 12 V ("high") and 6 flashing 12 V,
and its example (`0001 0001 0010 0011` = 1 1 2 3) agrees. The 1.x `DigitalOutputMode`
(0 floating, 1 low, 2 high, 3 flashing, 4 pulsatile) doesn't. `DigitalOutputState`
follows the manual. Unverified on a controller.

## 114: Charging Controllers, read as Charging Points

Register 114 counts the Charging Controllers of the system, on the backplane bus and over
Ethernet. The map places one Charging Point per Charging Controller, as 1.x did: a
SEC-3xxx and each SEC-1000 behind it host one Charging Point each. Over Ethernet, clients
of a Client/Server Group count too, which is out of scope (ADR 0001, 0005).

## x262: SOC in kWh or Wh

The meaning says "SOC in kWh", the coding "Integer [Wh]". The register is a placeholder
that reads 0; the map follows the coding (Wh).

## x308: a unit of A

The coding of "reset the last RFID tag" says "Integer [A]", but the register is a
command: any value above 0 clears x275. It isn't read (see the design's command
registers).

## 162: in German

The coding of the total current on L3 is in German ("-1, wenn Phasendrehung =
unbekannt"); it means the same as 158 and 160: -1 if the phase rotation is unknown.

## -1 for a Charging Point's phase currents

The manual documents -1 ("phase rotation unknown") for the group's total currents only.
A Charging Point's phase currents (x238-x243) read -1 as `None` too, as 1.x did: no real
current is -1 mA, so the sentinel can't hide a reading. Unverified whether a controller
sends it there.

## Holding or input registers

Table B-6 says holding (FC03) and input (FC04) registers return the same values. The map
reads holding registers.
