"""Shared register-array builders for decoder and integration tests."""

from __future__ import annotations


def global_regs() -> list[int]:
    """68 registers (100–167) with recognisable values for assertions."""
    regs = [0] * 68
    # designation: "CHARX TEST  " (10 words = 20 chars)
    text = "CHARX TEST          "
    for i, idx in enumerate(range(0, 10)):
        regs[idx] = (ord(text[i * 2]) << 8) | ord(text[i * 2 + 1])
    # SW version: "1.9.0   " (4 words)
    sw = "1.9.0   "
    for i in range(4):
        regs[10 + i] = (ord(sw[i * 2]) << 8) | ord(sw[i * 2 + 1])
    regs[14] = 2          # num_controllers
    # MAC ETH0: AA:BB:CC:DD:EE:FF
    regs[15] = 0xAABB
    regs[16] = 0xCCDD
    regs[17] = 0xEEFF
    # IP ETH0: 192.168.1.10
    regs[21] = 192
    regs[22] = 168
    regs[23] = 1
    regs[24] = 10
    # subnet ETH0: 255.255.255.0
    regs[29] = 255; regs[30] = 255; regs[31] = 255; regs[32] = 0
    # subnet ETH1: 255.255.0.0
    regs[33] = 255; regs[34] = 255; regs[35] = 0; regs[36] = 0
    # gateway ETH0: 192.168.1.1
    regs[37] = 192; regs[38] = 168; regs[39] = 1; regs[40] = 1
    # gateway ETH1: 0.0.0.0
    regs[45] = 1          # modem_registration = REGISTERED
    regs[46] = 4          # modem_signal_quality = GOOD
    regs[47] = 0          # num_non_critical_error
    regs[48] = 0          # num_status_ef
    regs[49] = 1          # num_status_a
    regs[50] = 1          # num_status_bcd
    regs[51] = 1          # num_charging
    # group_active_power: 11000 W = 11_000_000 mW
    mw = 11_000_000
    regs[52] = (mw >> 16) & 0xFFFF
    regs[53] = mw & 0xFFFF
    # group_current_l1: 16 A = 16_000 mA
    ma = 16_000
    regs[58] = (ma >> 16) & 0xFFFF
    regs[59] = ma & 0xFFFF
    # group_current_l2: unknown (-1)
    regs[60] = 0xFFFF
    regs[61] = 0xFFFF
    # group_current_l3: unknown (-1)
    regs[62] = 0xFFFF
    regs[63] = 0xFFFF
    regs[64] = 1          # availability = True
    regs[67] = 16         # dynamic_max_current = 16 A
    return regs


def cp_cfg_regs() -> list[int]:
    """24 registers (x100–x123)."""
    regs = [0] * 24
    regs[0] = 0    # interface_config = socket
    regs[1] = 32   # max_current_cfg = 32 A
    regs[2] = 6    # min_current_cfg = 6 A
    regs[20] = 5   # release_mode = MODBUS
    return regs


def cp_status_regs() -> list[int]:
    """77 registers (x232–x308)."""
    regs = [0] * 77
    # voltage L1: 230 V = 230_000 mV
    mv = 230_000
    regs[0] = (mv >> 16) & 0xFFFF
    regs[1] = mv & 0xFFFF
    # current L1: 16 A = 16_000 mA
    ma = 16_000
    regs[6] = (ma >> 16) & 0xFFFF
    regs[7] = ma & 0xFFFF
    # current L2/L3: unknown sentinel
    regs[8] = 0xFFFF; regs[9] = 0xFFFF
    regs[10] = 0xFFFF; regs[11] = 0xFFFF
    # active_power: 3680 W = 3_680_000 mW
    mw = 3_680_000
    regs[12] = (mw >> 16) & 0xFFFF
    regs[13] = mw & 0xFFFF
    # energy_active: 123456 Wh (4 words)
    wh = 123_456
    regs[18] = 0; regs[19] = 0
    regs[20] = (wh >> 16) & 0xFFFF
    regs[21] = wh & 0xFFFF
    # session_energy: 5000 Wh (4 words)
    swh = 5_000
    regs[57] = 0; regs[58] = 0
    regs[59] = (swh >> 16) & 0xFFFF
    regs[60] = swh & 0xFFFF
    # vehicle_status: C2 = 0x4332
    regs[67] = 0x4332
    # control registers (offset 68+)
    regs[68] = 1   # charging_release = True
    regs[69] = 16  # max_current = 16 A
    regs[72] = 1   # available = True
    regs[74] = 16  # watchdog_current = 16 A
    regs[75] = 65535  # watchdog_timer = disabled
    return regs
