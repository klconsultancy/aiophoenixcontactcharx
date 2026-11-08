"""The register map as ``modbus_connection`` components, and the controller over them.

Source: UM EN CHARX SEC, Revision 08, Appendix B3 (transcribed in
``docs/protocol/B3-modbus.md``). Every address is the manual's, a 0-based Modbus PDU
address. ``docs/design.md`` explains the layout and ``docs/errata.md`` where the
controller differs from the manual.
"""

import logging
import time
from typing import TYPE_CHECKING, Final

from modbus_connection import ModbusUnit
from modbus_connection.exceptions import (
    IllegalDataAddressError,
    IllegalFunctionError,
    ModbusConnectionError,
    ModbusError,
)
from modbus_connection.model import (
    Component,
    Device,
    UpdateReport,
    boolean,
    enum,
    flags,
    int32,
    int64,
    integer,
    raw_register,
    string,
    uint32,
    uint64,
)
from modbus_connection.model.fields import Eui48Field

from .enums import (
    ChargingInterface,
    EnergyMeterType,
    ErrorCode,
    ModemRegistration,
    ModemSignalQuality,
    OvercurrentMonitoring,
    ReleaseMode,
    TempMonitoring,
    VehicleStatus,
)
from .fields import IPv4OctetsField, VehicleStatusField

if TYPE_CHECKING:
    from collections.abc import Callable

_LOGGER = logging.getLogger(__name__)

#: The most Charging Points one Charging Controller hosts: its own and 11 SEC-1000s.
MAX_CHARGING_POINTS: Final = 12
#: A Charging Point's registers start at its number times this (x000-x999).
CHARGING_POINT_STRIDE: Final = 1000

# The registers report milli-units: mV, mA, mW, mVAR and mVA, and Wh for energy.
MILLI: Final = 0.001
# The raw pattern of -1 in a 32-bit register: the manual's "phase rotation unknown".
_MINUS_ONE_32: Final = 0xFFFF_FFFF
# A watchdog timer of 65535 s disables the watchdog (x307).
WATCHDOG_DISABLED: Final = 65535
# A read the controller refuses because it lacks the register, as opposed to a failure.
REFUSALS: Final = (IllegalDataAddressError, IllegalFunctionError)

# How long a left-out register stays out before it is tried again, in seconds.
RETRY_REFUSED_AFTER: Final = 3600.0

# What the Dynamic Max Current (167) reads while no limit is set.
NOT_SET: Final = 0xFFFF


class ControllerInfo(Component):
    """What identifies the Charging Controller and its network (100-146)."""

    # Each component states the address ranges the manual documents, so a read never
    # bridges into one it doesn't: a controller or firmware may refuse such an address,
    # which would fail the whole read (ADR 0006). Within a range, fields share reads.
    register_ranges = ((100, 146),)

    designation = string(100, 10)
    software_version = string(110, 4)
    # Every controller of the system, on the backplane bus and over Ethernet.
    charging_controllers = integer(114, signed=False)
    mac_eth0 = Eui48Field(115, count=3)
    mac_eth1 = Eui48Field(118, count=3)
    ip_eth0 = IPv4OctetsField(121)
    ip_eth1 = IPv4OctetsField(125)
    subnet_mask_eth0 = IPv4OctetsField(129)
    subnet_mask_eth1 = IPv4OctetsField(133)
    gateway_eth0 = IPv4OctetsField(137)  # placeholder, reads 0.0.0.0
    gateway_eth1 = IPv4OctetsField(141)  # placeholder, reads 0.0.0.0
    modem_registration = enum(145, ModemRegistration)
    modem_signal_quality = enum(146, ModemSignalQuality)


class Group(Component):
    """The whole group of Charging Controllers: its counts, totals and controls (147-167).

    The totals are those of the configured Charging Points, measured at the terminal
    point. Registers 165 and 166 (reset, system reset) are commands, not state: they come
    with the write API.
    """

    register_ranges = ((147, 164), (167, 167))

    # Counts of Charging Controllers
    non_critical_errors = integer(147, signed=False)
    status_e_or_f = integer(148, signed=False)
    status_a = integer(149, signed=False)
    status_b_c_or_d = integer(150, signed=False)
    charging = integer(151, signed=False)

    # Totals. A total current reads None while the phase rotation of a configured
    # Charging Point is unknown (the register holds -1).
    active_power = uint32(152, scale=MILLI, unit="W")
    reactive_power = int32(154, scale=MILLI, unit="var")
    apparent_power = uint32(156, scale=MILLI, unit="VA")
    current_l1 = int32(158, scale=MILLI, nan=_MINUS_ONE_32, unit="A")
    current_l2 = int32(160, scale=MILLI, nan=_MINUS_ONE_32, unit="A")
    current_l3 = int32(162, scale=MILLI, nan=_MINUS_ONE_32, unit="A")

    # Controls
    available = boolean(164)
    # 65535 while no dynamic limit is set (docs/errata.md), which reads None.
    dynamic_max_current = integer(167, signed=False, nan=NOT_SET, unit="A")


class ChargingPoint(Component):
    """One Charging Point: its configuration, status and controls (x100-x307).

    Declared at the offsets of the x000 block; ``CharxController`` places each one at its
    number times 1000. Register x308 (clear the last RFID UID) is a command, not state:
    it comes with the write API.
    """

    # In block coordinates; they move with the Charging Point's base offset.
    register_ranges = ((100, 123), (232, 307))

    # Configuration: x100 to x123
    interface = enum(100, ChargingInterface)
    max_current_config = integer(101, signed=False, unit="A")
    min_current_config = integer(102, signed=False, unit="A")
    rcm_configured = boolean(103)
    derating_start_temperature = integer(104, unit="°C")
    derating_stop_temperature = integer(105, unit="°C")
    derating_start_current = integer(106, signed=False, unit="A")
    derating_stop_current = integer(107, signed=False, unit="A")
    temperature_monitoring = enum(108, TempMonitoring)
    accept_status_d = boolean(109)
    # Only 0 (as per IEC 61851-1) is documented, so no enum.
    proximity_configuration = integer(110, signed=False)
    overcurrent_monitoring = enum(111, OvercurrentMonitoring)
    energy_meter_type = enum(112, EnergyMeterType)
    uid = string(113, 3)
    server_uid = string(116, 3)
    bus_position = integer(119, signed=False)
    release_mode = enum(120, ReleaseMode)
    # The manual calls it a placeholder that reads 0; a 1.7.3 controller repeats x113.
    rfid_reader_uid = string(121, 3)

    # Status: x232 to x299. A phase current reads None for the -1 of an unknown phase
    # rotation, as the Group's totals do.
    voltage_l1 = uint32(232, scale=MILLI, unit="V")
    voltage_l2 = uint32(234, scale=MILLI, unit="V")
    voltage_l3 = uint32(236, scale=MILLI, unit="V")
    current_l1 = int32(238, scale=MILLI, nan=_MINUS_ONE_32, unit="A")
    current_l2 = int32(240, scale=MILLI, nan=_MINUS_ONE_32, unit="A")
    current_l3 = int32(242, scale=MILLI, nan=_MINUS_ONE_32, unit="A")
    active_power = uint32(244, scale=MILLI, unit="W")
    reactive_power = int32(246, scale=MILLI, unit="var")
    apparent_power = uint32(248, scale=MILLI, unit="VA")
    # A lifetime counter that is in use never reads 0: right after a reconnect the
    # controller can report 0 while its meter starts, which a total_increasing sensor
    # would take for a meter reset (haphoenixcontactcharx#38). So 0 reads None.
    active_energy = uint64(250, scale=MILLI, nan=0, unit="kWh")
    reactive_energy = int64(254, scale=MILLI, unit="kvarh")
    apparent_energy = uint64(258, scale=MILLI, unit="kVAh")
    soc_energy = uint32(262, unit="Wh")  # placeholder (ISO 15118-20), reads 0
    soc = integer(264, signed=False, unit="%")  # placeholder (ISO 15118-20), reads 0
    evcc_id = string(265, 10)
    rfid_uid = string(275, 10)
    connection_time = uint32(285, unit="s")
    charging_duration = uint32(287, unit="s")
    session_energy = uint64(289, scale=MILLI, unit="kWh")
    error_code = flags(293, ErrorCode, count=2)
    digital_inputs = raw_register(295)  # one bit per input
    charging_current_duty_cycle = integer(296, signed=False, unit="%")
    charging_current = integer(297, signed=False, unit="A")
    cable_capacity = integer(298, signed=False, unit="A")
    vehicle_status = VehicleStatusField(299)

    # Controls: x300 to x307
    charging_release = boolean(300)
    max_current = integer(301, signed=False, unit="A")
    digital_outputs = raw_register(302)  # 4 bits per output; see DigitalOutputState
    locked = boolean(303)
    available = boolean(304)
    force_unlock = boolean(305)
    watchdog_current = integer(306, signed=False, unit="A")
    watchdog_timer = integer(307, signed=False, unit="s")

    @property
    def number(self) -> int:
        """The Charging Point's number, 1-12: the x of its x000 registers."""
        return self._index

    @property
    def is_connected(self) -> bool:
        """Whether a vehicle is connected (status B, C, D, E or F)."""
        return self.vehicle_status not in (
            None,
            VehicleStatus.A1,
            VehicleStatus.A2,
            VehicleStatus.IN,
        )

    @property
    def is_charging(self) -> bool:
        """Whether the vehicle is charging (status C2 or D2)."""
        return self.vehicle_status in (VehicleStatus.C2, VehicleStatus.D2)

    @property
    def has_error(self) -> bool:
        """Whether the Charging Point reports an error (status E0)."""
        return self.vehicle_status is VehicleStatus.E0

    @property
    def is_unavailable(self) -> bool:
        """Whether the Charging Point is out of service (status F0)."""
        return self.vehicle_status is VehicleStatus.F0

    @property
    def watchdog_enabled(self) -> bool | None:
        """Whether the watchdog runs; ``None`` until the timer has been read."""
        if self.watchdog_timer is None:
            return None
        return self.watchdog_timer != WATCHDOG_DISABLED


class _ChargingControllerCount(Component):
    """Register 114 on its own, which the setup reads to place the Charging Points."""

    register_ranges = ((114, 114),)
    charging_controllers = integer(114, signed=False)


def charging_point_name(number: int) -> str:
    """Return the name of Charging Point ``number`` in an ``UpdateReport``."""
    return f"charging_point_{number}"


class CharxController(Device):
    """A CHARX SEC-3xxx Charging Controller on a Modbus unit.

    ``device_info`` and ``group`` exist from the start; ``charging_points`` is empty
    until the first ``async_update()`` reads how many Charging Controllers the system has
    (register 114) and places one Charging Point for each, up to 12.
    """

    def __init__(
        self, unit: ModbusUnit, *, retry_refused_after: float = RETRY_REFUSED_AFTER
    ) -> None:
        """Map the controller on ``unit``; nothing is read until ``async_update()``.

        ``retry_refused_after`` is how long, in seconds, a register the controller refused
        stays left out before an update tries it again (default an hour). Raises
        ``ValueError`` if it isn't positive.
        """
        if retry_refused_after <= 0:
            msg = f"retry_refused_after must be positive, got {retry_refused_after}"
            raise ValueError(msg)
        super().__init__(unit)
        self.device_info = ControllerInfo(unit)
        self.group = Group(unit)
        self._charging_points: tuple[ChargingPoint, ...] = ()
        self._retry_refused_after = retry_refused_after
        # Per part, the fields left out because the controller refused them, each with the
        # time it is tried again.
        self._left_out: dict[str, dict[str, float]] = {}
        self._clock: Callable[[], float] = time.monotonic

    @property
    def charging_points(self) -> tuple[ChargingPoint, ...]:
        """The Charging Points, numbered 1 up; empty before the first update."""
        return self._charging_points

    @property
    def names(self) -> tuple[str, ...]:
        """The names ``async_update()`` reports on, in the order it reads them."""
        return (
            "device_info",
            "group",
            *(charging_point_name(cp.number) for cp in self._charging_points),
        )

    async def _async_setup(self) -> None:
        """Place a Charging Point per Charging Controller.

        Reads register 114 only: a refused identity register then fails ``device_info``
        in the report instead of the whole update (ADR 0006).
        """
        counter = _ChargingControllerCount(self.modbus_unit)
        await counter.async_update(notify=False)
        count = counter.charging_controllers or 0
        if count > MAX_CHARGING_POINTS:
            _LOGGER.warning(
                "The controller reports %d Charging Controllers; reading the first %d",
                count,
                MAX_CHARGING_POINTS,
            )
            count = MAX_CHARGING_POINTS
        if count == 0:
            _LOGGER.warning("The controller reports no Charging Controllers; reading none")
        points = tuple(
            ChargingPoint(self.modbus_unit, number, base_offset=number * CHARGING_POINT_STRIDE)
            for number in range(1, count + 1)
        )
        for point in points:
            # Device.async_poll finds each sub-system by attribute name.
            setattr(self, charging_point_name(point.number), point)
        self._charging_points = points

    async def async_update(self) -> UpdateReport:
        """Read the identity, the Group and every Charging Point, each on its own.

        The first call also places the Charging Points. The report names each part that
        refreshed and each that failed; a failed part keeps its last values.

        A register the controller refuses (illegal address or function) doesn't fail its
        part: the part's fields are read one by one, once, the refused ones are left out
        (they read ``None``, with a warning naming each register), and the part is read
        again in the same update. Any other error during that search fails only the part,
        and the next update searches again. A left-out register is tried again once
        ``retry_refused_after`` has passed, so a refusal that was temporary heals.

        Raises ``ModbusConnectionError`` when the link is down and ``ModbusTimeoutError``
        when nothing answers, like ``Device.async_poll``.
        """
        await self.async_ensure_setup()
        if self._left_out:
            await self._retry_left_out()
        report = await self.async_poll(self.names)
        refused = [name for name, err in report.failed.items() if isinstance(err, REFUSALS)]
        retry = []
        for name in refused:
            error = await self._leave_out_refused_fields(name)
            if error is None:
                retry.append(name)
            else:
                report.failed[name] = error
        if retry:
            # The refusals stay in the report until the retry answers: async_poll raises a
            # timeout only while the report is empty, and a part that times out on the
            # retry must fail alone rather than end the update.
            await self.async_poll(retry, report)
            for name in retry:
                if name in report.updated:
                    del report.failed[name]
        return report

    def _fresh(self, name: str) -> Component:
        """Build a new, unread instance of part ``name``, at the same addresses."""
        part: Component = getattr(self, name)
        if isinstance(part, ChargingPoint):
            return ChargingPoint(
                self.modbus_unit, part.number, base_offset=part.number * CHARGING_POINT_STRIDE
            )
        return type(part)(self.modbus_unit)

    async def _probe(self, name: str, field: str) -> ModbusError | None:
        """Read ``field`` of part ``name`` on its own; return the error, or ``None``.

        A lost connection propagates.
        """
        probe = self._fresh(name)
        probe.restrict_fields([field])
        try:
            await probe.async_update(notify=False)
        except ModbusConnectionError:
            raise
        except ModbusError as err:
            return err
        return None

    async def _leave_out_refused_fields(self, name: str) -> ModbusError | None:
        """Read each field of part ``name`` on its own and leave out those refused.

        Returns the error that stopped the search, or ``None``. A lost connection
        propagates.
        """
        part: Component = getattr(self, name)
        kept: list[str] = []
        refused: list[str] = []
        for field, resolved in part.resolved_fields.items():
            error = await self._probe(name, field)
            if error is None:
                kept.append(field)
            elif isinstance(error, REFUSALS):
                refused.append(f"register {resolved.address} ({name}.{field})")
            else:
                return error  # nothing is left out on a partial search
        if not refused:
            return None  # every field answers on its own
        if kept:
            for description in refused:
                _LOGGER.warning("The controller refuses %s; reading it as None", description)
        else:
            _LOGGER.warning("The controller refuses every register of %s; reading it as None", name)
        part.restrict_fields(kept)
        retry_at = self._clock() + self._retry_refused_after
        left_out = self._left_out.setdefault(name, {})
        for field in part.declared_fields:
            if field not in kept:
                # A field left out before keeps its own time.
                left_out.setdefault(field, retry_at)
        return None

    async def _retry_left_out(self) -> None:
        """Read each left-out field whose time has come again; put back those that answer.

        Any error but a lost connection keeps a field out for another interval.
        """
        now = self._clock()
        later = now + self._retry_refused_after
        for name, left_out in list(self._left_out.items()):
            back: list[str] = []
            for field in [field for field, retry_at in left_out.items() if retry_at <= now]:
                if await self._probe(name, field) is None:
                    back.append(field)
                else:
                    left_out[field] = later
            if back and not await self._put_back(name, back):
                for field in back:
                    left_out[field] = later

    async def _put_back(self, name: str, back: list[str]) -> bool:
        """Replace part ``name`` by one that reads ``back`` too; whether that worked.

        ``restrict_fields`` can't be undone, so the part becomes a new instance under the
        same name. It is read first and replaces the old one only if that read succeeds,
        so a failure keeps the part's last values. A lost connection propagates.
        """
        left_out = self._left_out[name]
        still_out = [field for field in left_out if field not in back]
        part = self._fresh(name)
        if still_out:
            part.restrict_fields([f for f in part.declared_fields if f not in still_out])
        try:
            await part.async_update(notify=False)
        except ModbusConnectionError:
            raise
        except ModbusError:
            return False
        for field in back:
            del left_out[field]
            _LOGGER.info(
                "The controller answers register %d (%s.%s) again",
                part.resolved_fields[field].address,
                name,
                field,
            )
        if not left_out:
            del self._left_out[name]
        self._replace(name, part)
        return True

    def _replace(self, name: str, part: Component) -> None:
        """Put ``part`` in place of the part named ``name``."""
        setattr(self, name, part)
        if isinstance(part, ChargingPoint):
            self._charging_points = tuple(
                part if cp.number == part.number else cp for cp in self._charging_points
            )
