# -*- coding: utf-8 -*-
"""断在 rt_assert_handler，读 r4-r7（调用方保存的 serial 等），看哪一个是设备指针"""
import sys
import time

from pyocd.core.helpers import ConnectHelper
from pyocd.core.target import Target

HANDLER = int(sys.argv[1], 16)


def main():
    with ConnectHelper.session_with_chosen_probe(target_override="r7ka8p1kf") as s:
        t = s.target
        t.reset_and_halt()
        t.set_breakpoint(HANDLER)
        t.resume()
        end = time.time() + 8
        while time.time() < end and t.get_state() != Target.State.HALTED:
            time.sleep(0.03)
        if t.get_state() != Target.State.HALTED:
            print("NOT HIT")
            t.remove_breakpoint(HANDLER)
            t.resume()
            return 0

        print(f"PC=0x{t.read_core_register('pc'):08X}  lr=0x{t.read_core_register('lr'):08X}")
        for r in ("r0", "r1", "r2", "r3", "r4", "r5", "r6", "r7", "r8", "r9"):
            v = t.read_core_register(r)
            note = ""
            if 0x22000000 <= v <= 0x22174000:
                try:
                    raw = bytes(t.read_memory_block8(v, 8)).split(b"\x00")[0]
                    s_ = raw.decode("ascii", "replace")
                    if s_.isprintable() and len(s_) >= 2:
                        note = f"  -> str '{s_}'"
                    else:
                        note = "  -> (RAM int)"
                except Exception:
                    pass
            print(f"  {r:3s} = 0x{v:08X}{note}")
        t.remove_breakpoint(HANDLER)
        t.resume()
    return 0


if __name__ == "__main__":
    sys.exit(main())
