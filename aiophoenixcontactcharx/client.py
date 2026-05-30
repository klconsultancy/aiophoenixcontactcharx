"""Async Modbus/TCP client for Phoenix Contact CHARX SEC EV charging controllers."""

from __future__ import annotations

import logging
from types import TracebackType
from typing import Any

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException

from .exceptions import (
    CharxConnectionError,
    CharxInvalidDataError,
    CharxModbusError,
    CharxTimeoutError,
)
from .models import (
    CharxData,
    ChargingPointConfig,
    ChargingPointControl,
    ChargingPointData,
    ChargingPointStatus,
    DeviceInfo,
    EnergyMeterType,
    ModemRegistration,
    ModemSignalQuality,
    ReleaseMode,
    TempMonitoring,
)
from .registers import (
    CP_CFG_COUNT,
    CP_CFG_OFFSET,
    CP_STATUS_COUNT,
    CP_STATUS_OFFSET,
    GLOBAL_BASE,
    GLOBAL_COUNT,
    GROUP_AVAILABILITY,
    GROUP_DYNAMIC_MAX_CURRENT,
    cp_register,
)

_LOGGER = logging.getLogger(__name__)

_UNIT_ID = 1       # CHARX always answers on Modbus address 1
_DEFAULT_PORT = 502
_DEFAULT_TIMEOUT = 10  # seconds


# ---------------------------------------------------------------------------
# Helper functions for converting raw Modbus register lists
# ---------------------------------------------------------------------------

def _u32(regs: list[int], offset: int) -> int:
    """Unsigned 32-bit from two consecutive 16-bit registers (MSW first)."""
    return (regs[offset] << 16) | regs[offset + 1]


def _s32(regs: list[int], offset: int) -> int:
    """Signed 32-bit from two consecutive 16-bit registers (MSW first)."""
    value = _u32(regs, offset)
    return value if value < 0x80000000 else value - 0x100000000


def _u64(regs: list[int], offset: int) -> int:
    """Unsigned 64-bit from four consecutive 16-bit registers (MSW first)."""
    return (
        (regs[offset] << 48)
        | (regs[offset + 1] << 32)
        | (regs[offset + 2] << 16)
        | regs[offset + 3]
    )


def _s64(regs: list[int], offset: int) -> int:
    """Signed 64-bit from four consecutive 16-bit registers (MSW first)."""
    value = _u64(regs, offset)
    return value if value < 0x8000000000000000 else value - 0x10000000000000000


def _ascii(regs: list[int], offset: int, num_words: int) -> str:
    """Decode ASCII string from consecutive 16-bit registers (2 chars per word)."""
    chars: list[str] = []
    for reg in regs[offset : offset + num_words]:
        high = (reg >> 8) & 0xFF
        low = reg & 0xFF
        if high:
            chars.append(chr(high))
        if low:
            chars.append(chr(low))
    return "".join(chars).rstrip("\x00").strip()


def _vehicle_status(reg: int) -> str:
    """Decode 2-char IEC 61851-1 status from a single 16-bit register."""
    high = (reg >> 8) & 0xFF
    low = reg & 0xFF
    if high and low:
        return chr(high) + chr(low)
    return "A1"


def _ip(regs: list[int], offset: int) -> str:
    """Decode IPv4 address from 4 consecutive octet registers."""
    return ".".join(str(regs[offset + i]) for i in range(4))


def _mac(regs: list[int], offset: int) -> str:
    """Decode MAC address from 3 consecutive 16-bit HEX registers."""
    bytes_: list[str] = []
    for reg in regs[offset : offset + 3]:
        bytes_.append(f"{(reg >> 8) & 0xFF:02X}")
        bytes_.append(f"{reg & 0xFF:02X}")
    return ":".join(bytes_)


def _maybe_phase_current(regs: list[int], offset: int) -> int | None:
    """Read a signed 32-bit current value; return None for the −1 sentinel."""
    value = _s32(regs, offset)
    return None if value == -1 else value


# ---------------------------------------------------------------------------
# CharxClient
# ---------------------------------------------------------------------------

class CharxClient:
    """Async Modbus/TCP client for a CHARX SEC-3xxx charging controller.

    Usage::

        async with CharxClient("192.168.1.100") as client:
            data = await client.fetch_data(num_charging_points=1)
    """

    def __init__(
        self,
        host: str,
        port: int = _DEFAULT_PORT,
        timeout: int = _DEFAULT_TIMEOUT,
    ) -> None:
        self._host = host
        self._port = port
        self._timeout = timeout
        self._client: AsyncModbusTcpClient = AsyncModbusTcpClient(
            host=host,
            port=port,
            timeout=timeout,
        )

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Open the Modbus/TCP connection."""
        try:
            connected = await self._client.connect()
        except Exception as err:
            raise CharxConnectionError(
                f"Cannot connect to CHARX at {self._host}:{self._port}: {err}"
            ) from err
        if not connected:
            raise CharxConnectionError(
                f"Cannot connect to CHARX at {self._host}:{self._port}"
            )
        _LOGGER.debug("Connected to CHARX at %s:%d", self._host, self._port)

    async def disconnect(self) -> None:
        """Close the Modbus/TCP connection."""
        self._client.close()

    @property
    def connected(self) -> bool:
        """True when the underlying transport is open."""
        return self._client.connected

    async def __aenter__(self) -> "CharxClient":
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.disconnect()

    # ------------------------------------------------------------------
    # Low-level register I/O
    # ------------------------------------------------------------------

    async def _read(self, address: int, count: int) -> list[int]:
        """Read *count* holding registers starting at *address*.

        Reconnects once if the transport has dropped.
        """
        if not self._client.connected:
            _LOGGER.debug("Connection lost; reconnecting to %s", self._host)
            await self.connect()

        try:
            result = await self._client.read_holding_registers(
                address=address,
                count=count,
                device_id=_UNIT_ID,
            )
        except ModbusException as err:
            raise CharxModbusError(
                f"Modbus error reading {address}+{count}: {err}"
            ) from err
        except Exception as err:
            raise CharxConnectionError(
                f"Connection error reading {address}+{count}: {err}"
            ) from err

        if result.isError():
            raise CharxModbusError(
                f"Device returned Modbus exception for {address}+{count}: {result}"
            )

        if len(result.registers) != count:
            raise CharxInvalidDataError(
                f"Expected {count} registers at {address}, got {len(result.registers)}"
            )

        return result.registers

    async def _write_register(self, address: int, value: int) -> None:
        """Write a single holding register."""
        if not self._client.connected:
            await self.connect()
        try:
            result = await self._client.write_register(
                address=address,
                value=value,
                device_id=_UNIT_ID,
            )
        except ModbusException as err:
            raise CharxModbusError(
                f"Modbus error writing {address}={value}: {err}"
            ) from err
        except Exception as err:
            raise CharxConnectionError(
                f"Connection error writing {address}={value}: {err}"
            ) from err

        if result.isError():
            raise CharxModbusError(
                f"Device returned exception writing {address}={value}: {result}"
            )

    # ------------------------------------------------------------------
    # Parsed reads
    # ------------------------------------------------------------------

    async def get_device_info(self) -> DeviceInfo:
        """Read global registers 100–167 and return a DeviceInfo snapshot."""
        regs = await self._read(GLOBAL_BASE, GLOBAL_COUNT)
        # offset = register_address - GLOBAL_BASE
        return DeviceInfo(
            designation=_ascii(regs, 0, 10),
            software_version=_ascii(regs, 10, 4),
            num_controllers=regs[14],
            mac_eth0=_mac(regs, 15),
            mac_eth1=_mac(regs, 18),
            ip_eth0=_ip(regs, 21),
            ip_eth1=_ip(regs, 25),
            modem_registration=ModemRegistration(
                regs[45] if regs[45] in ModemRegistration._value2member_map_ else 4
            ),
            modem_signal_quality=ModemSignalQuality(
                regs[46] if regs[46] in ModemSignalQuality._value2member_map_ else 0
            ),
            num_non_critical_error=regs[47],
            num_status_ef=regs[48],
            num_status_a=regs[49],
            num_status_bcd=regs[50],
            num_charging=regs[51],
            group_active_power_mw=_u32(regs, 52),
            group_reactive_power_mvar=_s32(regs, 54),
            group_apparent_power_mva=_u32(regs, 56),
            group_current_l1_ma=_maybe_phase_current(regs, 58),
            group_current_l2_ma=_maybe_phase_current(regs, 60),
            group_current_l3_ma=_maybe_phase_current(regs, 62),
            availability=bool(regs[64]),
            dynamic_max_current_a=regs[67],
        )

    async def get_charging_point_config(
        self, charging_point: int
    ) -> ChargingPointConfig:
        """Read configuration registers for one charging point."""
        base = cp_register(charging_point, CP_CFG_OFFSET)
        regs = await self._read(base, CP_CFG_COUNT)
        raw_meter = regs[12]
        meter_type = (
            EnergyMeterType(raw_meter)
            if raw_meter in EnergyMeterType._value2member_map_
            else EnergyMeterType.UNKNOWN
        )
        return ChargingPointConfig(
            charging_point=charging_point,
            interface_config=regs[0],
            max_current_cfg_a=regs[1],
            min_current_cfg_a=regs[2],
            rcm_configured=bool(regs[3]),
            temp_lower_thr_c=regs[4],
            temp_upper_thr_c=regs[5],
            current_derating_start_a=regs[6],
            current_derating_stop_a=regs[7],
            temp_monitoring=TempMonitoring(
                regs[8] if regs[8] in TempMonitoring._value2member_map_ else 0
            ),
            accept_status_d=bool(regs[9]),
            energy_meter_type=meter_type,
            uid=_ascii(regs, 13, 3),
            server_uid=_ascii(regs, 16, 3),
            bus_position=regs[19],
            release_mode=ReleaseMode(
                regs[20] if regs[20] in ReleaseMode._value2member_map_ else 0
            ),
        )

    async def get_charging_point_status_and_control(
        self, charging_point: int
    ) -> tuple[ChargingPointStatus, ChargingPointControl]:
        """Read status (x232–x299) and control (x300–x308) in one Modbus request."""
        base = cp_register(charging_point, CP_STATUS_OFFSET)
        regs = await self._read(base, CP_STATUS_COUNT)
        # offsets within this read (0 = register x232)
        status = ChargingPointStatus(
            charging_point=charging_point,
            voltage_l1_mv=_u32(regs, 0),
            voltage_l2_mv=_u32(regs, 2),
            voltage_l3_mv=_u32(regs, 4),
            current_l1_ma=_maybe_phase_current(regs, 6),
            current_l2_ma=_maybe_phase_current(regs, 8),
            current_l3_ma=_maybe_phase_current(regs, 10),
            active_power_mw=_s32(regs, 12),
            reactive_power_mvar=_s32(regs, 14),
            apparent_power_mva=_u32(regs, 16),
            energy_active_wh=_u64(regs, 18),
            energy_reactive_varh=_s64(regs, 22),
            energy_apparent_vah=_u64(regs, 26),
            # offsets 30–32: SOC placeholders (skip)
            last_evcc_id=_ascii(regs, 33, 10),
            last_rfid=_ascii(regs, 43, 10),
            connection_time_s=_u32(regs, 53),
            charging_duration_s=_u32(regs, 55),
            session_energy_wh=_u64(regs, 57),
            error_code=(_u32(regs, 61)),           # MSB=293 LSB=294 → one 32-bit word
            digital_inputs=regs[63],
            setpoint_percent=regs[64],
            setpoint_a=regs[65],
            cable_capacity_a=regs[66],
            vehicle_status=_vehicle_status(regs[67]),
        )
        # Control registers start at offset 68 (absolute x300 → relative to x232 = 68)
        control = ChargingPointControl(
            charging_point=charging_point,
            charging_release=bool(regs[68]),
            max_current_a=regs[69],
            digital_outputs=regs[70],
            locking=bool(regs[71]),
            available=bool(regs[72]),
            watchdog_current_a=regs[74],
            watchdog_timer_s=regs[75],
        )
        return status, control

    async def fetch_data(self, num_charging_points: int) -> CharxData:
        """Fetch a complete data snapshot for all charging points.

        Makes 1 + 2×num_charging_points Modbus requests total.
        """
        device_info = await self.get_device_info()
        charging_points: list[ChargingPointData] = []
        for cp in range(1, num_charging_points + 1):
            config = await self.get_charging_point_config(cp)
            status, control = await self.get_charging_point_status_and_control(cp)
            charging_points.append(
                ChargingPointData(
                    charging_point=cp,
                    config=config,
                    status=status,
                    control=control,
                )
            )
        return CharxData(device_info=device_info, charging_points=charging_points)

    # ------------------------------------------------------------------
    # Control writes
    # ------------------------------------------------------------------

    async def set_charging_release(
        self, charging_point: int, enabled: bool
    ) -> None:
        """Enable or disable charging release for a charging point.

        The charging point must be configured for Modbus release mode.
        """
        await self._write_register(
            cp_register(charging_point, 300), int(enabled)
        )

    async def set_max_current(self, charging_point: int, current_a: int) -> None:
        """Set the maximum charging current (6–80 A).

        Values outside this range cause the charging release to be withdrawn.
        """
        if not 6 <= current_a <= 80:
            raise ValueError(f"Max current must be 6–80 A, got {current_a}")
        await self._write_register(cp_register(charging_point, 301), current_a)

    async def set_availability(
        self, charging_point: int, available: bool
    ) -> None:
        """Set charging point availability (status F).

        The charging point must be configured for Modbus release mode.
        """
        await self._write_register(
            cp_register(charging_point, 304), int(available)
        )

    async def set_dynamic_max_current(self, current_a: int) -> None:
        """Set the dynamic maximum current for the load management group."""
        await self._write_register(GROUP_DYNAMIC_MAX_CURRENT, current_a)

    async def set_watchdog(
        self, charging_point: int, timer_s: int, fallback_current_a: int
    ) -> None:
        """Configure the Modbus watchdog for a charging point.

        If no new value is written within timer_s seconds the device falls
        back to fallback_current_a. Set timer_s=65535 to disable.
        """
        await self._write_register(
            cp_register(charging_point, 306), fallback_current_a
        )
        await self._write_register(
            cp_register(charging_point, 307), timer_s
        )

    async def force_unlock(self, charging_point: int) -> None:
        """Force-unlock the charging connector."""
        await self._write_register(cp_register(charging_point, 305), 1)

    async def reset_last_rfid(self, charging_point: int) -> None:
        """Clear the last RFID UID stored in register x275."""
        await self._write_register(cp_register(charging_point, 308), 1)
