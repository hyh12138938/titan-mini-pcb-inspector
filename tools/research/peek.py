# -*- coding: utf-8 -*-
"""从板子读一个/多个全局符号的值（会话级探针）。

用法:
  python peek.py --elf <elf> s_frames s_fps s_my --gap 2
输出每个符号的地址与两次读数，并标出是否在变化。
"""
import argparse
import re
import subprocess
import time

from pyocd.core.helpers import ConnectHelper

NM = r"D:\tools\arm-gnu-toolchain-13.3.rel1-mingw-w64-i686-arm-none-eabi\bin\arm-none-eabi-nm.exe"


def sym_table(elf):
    out = subprocess.run([NM, elf], capture_output=True, text=True, errors="replace").stdout
    table = {}
    for line in out.splitlines():
        m = re.match(r"^([0-9a-fA-F]{8})\s+(\w)\s+(\S+)$", line)
        if m:
            table[m.group(3)] = (int(m.group(1), 16), m.group(2))
    return table


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--elf", required=True)
    ap.add_argument("names", nargs="+")
    ap.add_argument("--gap", type=float, default=2.0)
    ap.add_argument("--size", type=int, default=4)
    a = ap.parse_args()

    tab = sym_table(a.elf)

    with ConnectHelper.session_with_chosen_probe(target_override="r7ka8p1kf") as s:
        t = s.target
        t.halt()
        first = {}
        for n in a.names:
            if n not in tab:
                first[n] = None
                continue
            addr = tab[n][0]
            first[n] = int.from_bytes(bytes(t.read_memory_block8(addr, a.size)), "little")
        t.resume()

        time.sleep(a.gap)

        t.halt()
        second = {}
        for n in a.names:
            if n not in tab:
                second[n] = None
                continue
            addr = tab[n][0]
            second[n] = int.from_bytes(bytes(t.read_memory_block8(addr, a.size)), "little")
        t.resume()

    for n in a.names:
        if first[n] is None:
            print(f"  {n:<16} NOT FOUND")
            continue
        addr = tab[n][0]
        delta = second[n] - first[n]
        flag = "CHANGED" if delta else "static "
        print(f"  {n:<16} @0x{addr:08X}  {first[n]:>12} -> {second[n]:>12}  [{flag} d={delta}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
