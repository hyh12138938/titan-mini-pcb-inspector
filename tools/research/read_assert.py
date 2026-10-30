# -*- coding: utf-8 -*-
"""读取断言记录（rgb_lcd 的 assert_dump.c）"""
import sys

from pyocd.core.helpers import ConnectHelper

EX = 0x22020CB8
FUNC = 0x22020D08
HIT = 0x22020D5C
LINE = 0x22020D58
COUNT = 0x22020D60


def rd_str(t, addr, n=80):
    raw = bytes(t.read_memory_block8(addr, n)).split(b"\x00")[0]
    return raw.decode("ascii", "replace")


def main():
    with ConnectHelper.session_with_chosen_probe(target_override="r7ka8p1kf") as s:
        t = s.target
        t.halt()
        print(f"PC=0x{t.read_core_register('pc'):08X}")
        print("hit   =", t.read32(HIT))
        print("count =", t.read32(COUNT))
        print("line  =", t.read32(LINE))
        print("ex    =", rd_str(t, EX))
        print("func  =", rd_str(t, FUNC))
        t.resume()
    return 0


if __name__ == "__main__":
    sys.exit(main())
