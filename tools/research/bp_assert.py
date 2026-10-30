# -*- coding: utf-8 -*-
"""在 rt_assert_handler 下断点，命中后读 r0/r1/r2 = 表达式/函数/行号"""
import sys
import time

from pyocd.core.helpers import ConnectHelper
from pyocd.core.target import Target

BP = int(sys.argv[1], 16) if len(sys.argv) > 1 else 0x02018840


def rd_str(t, addr, n=96):
    if addr < 0x02000000 or addr > 0x08100000:
        return f"<bad ptr 0x{addr:08X}>"
    try:
        raw = bytes(t.read_memory_block8(addr, n)).split(b"\x00")[0]
        return raw.decode("ascii", "replace")
    except Exception as e:
        return f"<read fail {e}>"


def main():
    with ConnectHelper.session_with_chosen_probe(target_override="r7ka8p1kf") as s:
        t = s.target
        t.reset_and_halt()
        t.set_breakpoint(BP)
        t.resume()

        deadline = time.time() + 8
        while time.time() < deadline:
            if t.get_state() == Target.State.HALTED:
                break
            time.sleep(0.05)

        if t.get_state() != Target.State.HALTED:
            print(f"8 秒内没有命中断点 0x{BP:08X}（说明这条断言路径没被走到）")
            t.remove_breakpoint(BP)
            t.resume()
            return 0

        pc = t.read_core_register("pc")
        r0 = t.read_core_register("r0")
        r1 = t.read_core_register("r1")
        r2 = t.read_core_register("r2")
        print(f"命中! PC=0x{pc:08X}")
        print(f"  r0(ex_string) = 0x{r0:08X}  -> {rd_str(t, r0)}")
        print(f"  r1(func)      = 0x{r1:08X}  -> {rd_str(t, r1)}")
        print(f"  r2(line)      = {r2}")
        print(f"  lr            = 0x{t.read_core_register('lr'):08X}")
        t.remove_breakpoint(BP)
        t.resume()
    return 0


if __name__ == "__main__":
    sys.exit(main())
