# -*- coding: utf-8 -*-
"""读 GPT7（背光 PWM）寄存器，判断 PWM 是否在输出"""
import sys

from pyocd.core.helpers import ConnectHelper

BASES = (0x40322700, 0x50322700)

REG = {
    0x00: "GTWP", 0x04: "GTSTR", 0x08: "GTSTP", 0x0C: "GTCLR",
    0x2C: "GTCR", 0x30: "GTUDDTYC", 0x34: "GTOR", 0x38: "GTNOR",
    0x3C: "GTOCR", 0x40: "GTOSR", 0x4C: "GTCCR", 0x50: "GTPR", 0x54: "GTCNT",
}


def main():
    with ConnectHelper.session_with_chosen_probe(target_override="r7ka8p1kf") as s:
        t = s.target
        t.halt()
        for base in BASES:
            print(f"=== GPT7 @ 0x{base:08X} ===")
            ok = True
            for off, name in REG.items():
                try:
                    v = t.read32(base + off)
                except Exception as e:
                    print(f"  {name:8s} <读取失败 {e}>")
                    ok = False
                    break
                print(f"  {name:8s} (+0x{off:02X}) = 0x{v:08X}  ({v})")
            if not ok:
                continue
            # 解读
            gtcr = t.read32(base + 0x2C)
            udd = t.read32(base + 0x30)
            gtpr = t.read32(base + 0x50)
            gtccr = t.read32(base + 0x4C)
            gtcnt = t.read32(base + 0x54)
            print(f"  --> period={gtpr} duty={gtccr} counter={gtcnt}")
            print(f"  --> GTUDDTYC output enable bits: OAE={'1' if (udd>>16)&1 else '0'} "
                  f"OBE={'1' if (udd>>17)&1 else '0'}  UD(bits1:0)=0b{(udd & 3):02b}")
            print(f"  --> GTCR.MD(bits18:16)=0b{((gtcr>>16) & 7):03b} (0=saw,1=triangle; "
                  f"saw+pwm needs GTUDDTYC)")
        t.resume()
    return 0


if __name__ == "__main__":
    sys.exit(main())
