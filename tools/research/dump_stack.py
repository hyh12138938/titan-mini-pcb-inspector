# -*- coding: utf-8 -*-
"""停机读栈，取出返回地址，用 addr2line 还原调用链"""
import struct
import sys

from pyocd.core.helpers import ConnectHelper

SP_FALLBACK = 0x22020460


def main():
    with ConnectHelper.session_with_chosen_probe(target_override="r7ka8p1kf") as s:
        t = s.target
        t.halt()
        sp = t.read_core_register("sp")
        pc = t.read_core_register("pc")
        if sp < 0x22000000 or sp > 0x22180000:
            sp = SP_FALLBACK
        print(f"PC=0x{pc:08X} SP=0x{sp:08X}")
        data = bytes(t.read_memory_block8(sp, 4 * 96))
        words = struct.unpack("<96I", data)
        seen = []
        for w in words:
            if 0x02000000 <= w < 0x02100000 and (w & 1):
                a = w & ~1
                if a not in seen:
                    seen.append(a)
        print("CANDIDATES " + " ".join(f"0x{a:08X}" for a in seen[:40]))
        t.resume()


if __name__ == "__main__":
    sys.exit(main())
