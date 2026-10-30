# -*- coding: utf-8 -*-
"""停机读取目标状态：PC / 故障寄存器 / 我们的调试变量"""
import sys

from pyocd.core.helpers import ConnectHelper

SYMS = {
    "dbg_err":      0x22020E08,
    "dbg_result":   0x22020E0C,
    "dbg_good_q":   0x22020E18,
    "dbg_defect_q": 0x22020E1C,
}

FAULT = {
    "CFSR":  0xE000ED28,
    "HFSR":  0xE000ED2C,
    "MMFAR": 0xE000ED34,
    "BFAR":  0xE000ED38,
    "SHCSR": 0xE000ED24,
}


def main():
    with ConnectHelper.session_with_chosen_probe(target_override="r7ka8p1kf") as s:
        t = s.target
        t.halt()
        print("=== core ===")
        for r in ("pc", "lr", "sp", "xpsr", "r0", "r1"):
            try:
                print(f"  {r:5s} = 0x{t.read_core_register(r):08X}")
            except Exception as e:
                print(f"  {r:5s} = <{e}>")

        print("=== fault regs ===")
        for name, addr in FAULT.items():
            try:
                print(f"  {name:6s} = 0x{t.read32(addr):08X}")
            except Exception as e:
                print(f"  {name:6s} = <{e}>")

        print("=== app vars ===")
        for name, addr in SYMS.items():
            try:
                v = t.read32(addr)
                print(f"  {name:12s} @0x{addr:08X} = {v} (0x{v:08X})")
            except Exception as e:
                print(f"  {name:12s} <{e}>")

        try:
            out = bytes(t.read_memory_block8(0x22020F20, 2))
            print(f"  pad_output  @0x22020F20 = {list(out)} (int8: {out[0] if out[0]<128 else out[0]-256}, {out[1] if out[1]<128 else out[1]-256})")
        except Exception as e:
            print(f"  pad_output <{e}>")

        t.resume()


if __name__ == "__main__":
    sys.exit(main())
