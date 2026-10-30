# -*- coding: utf-8 -*-
"""通过 SWD 直接写板子 RAM 里的 static volatile 变量（console 不通时的调参通道）。

用法:
  python poke.py --elf <elf> s_gain_r=24 s_gain_g=18 s_gain_b=21 s_dirty=1
  python poke.py --elf <elf> --show s_gain_r s_my      # 只读

说明: 地址从 ELF 的符号表现取，不要写死；写完后 s_dirty=1 让下一帧重建 LUT。
"""
import argparse
import re
import subprocess

from pyocd.core.helpers import ConnectHelper

NM = r"D:\tools\arm-gnu-toolchain-13.3.rel1-mingw-w64-i686-arm-none-eabi\bin\arm-none-eabi-nm.exe"


def sym_table(elf):
    out = subprocess.run([NM, elf], capture_output=True, text=True, errors="replace").stdout
    table = {}
    for line in out.splitlines():
        m = re.match(r"^([0-9a-fA-F]{8})\s+(\w)\s+(\S+)$", line)
        if m:
            table[m.group(3)] = int(m.group(1), 16)
    return table


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--elf", required=True)
    ap.add_argument("--size", type=int, default=4)
    ap.add_argument("--show", nargs="*", default=None)
    ap.add_argument("assign", nargs="*", default=[])
    a = ap.parse_args()

    tab = sym_table(a.elf)

    todo = []
    for item in a.assign:
        if "=" not in item:
            print(f"bad assignment: {item}")
            return 2
        name, val = item.split("=", 1)
        if name not in tab:
            print(f"symbol not found: {name}")
            return 2
        todo.append((name, tab[name], int(val, 0)))

    with ConnectHelper.session_with_chosen_probe(target_override="r7ka8p1kf") as s:
        t = s.target
        t.halt()
        try:
            for name, addr, val in todo:
                t.write_memory_block8(addr, bytes(val.to_bytes(a.size, "little")))
                back = int.from_bytes(bytes(t.read_memory_block8(addr, a.size)), "little")
                mark = "ok" if back == val else f"MISMATCH({back})"
                print(f"  {name:<14} @0x{addr:08X} <- {val:<10} {mark}")
            for name in (a.show or []):
                if name not in tab:
                    print(f"  {name:<14} NOT FOUND")
                    continue
                addr = tab[name]
                v = int.from_bytes(bytes(t.read_memory_block8(addr, a.size)), "little")
                print(f"  {name:<14} @0x{addr:08X} = {v}")
        finally:
            t.resume()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
