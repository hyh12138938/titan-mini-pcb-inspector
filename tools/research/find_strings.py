# -*- coding: utf-8 -*-
"""从栈上找 rodata 指针，读回断言表达式字符串"""
import struct
import sys

from pyocd.core.helpers import ConnectHelper


def ascii_ratio(b):
    if not b:
        return 0.0
    ok = sum(1 for c in b if 32 <= c < 127)
    return ok / len(b)


def main():
    with ConnectHelper.session_with_chosen_probe(target_override="r7ka8p1kf") as s:
        t = s.target
        t.halt()
        sp = t.read_core_register("sp")
        pc = t.read_core_register("pc")
        print(f"PC=0x{pc:08X} SP=0x{sp:08X}")
        if not (0x22000000 <= sp <= 0x22180000):
            print("SP 不在 SRAM，放弃")
            t.resume()
            return 1
        data = bytes(t.read_memory_block8(sp, 4 * 160))
        words = struct.unpack("<160I", data)
        for i, w in enumerate(words):
            if 0x02000000 <= w <= 0x02050000:
                try:
                    raw = bytes(t.read_memory_block8(w, 56))
                except Exception:
                    continue
                raw = raw.split(b"\x00")[0]
                if len(raw) >= 6 and ascii_ratio(raw) > 0.85:
                    print(f"  [{i:3d}] 0x{w:08X}  {raw.decode('ascii', 'replace')}")
        t.resume()
    return 0


if __name__ == "__main__":
    sys.exit(main())
