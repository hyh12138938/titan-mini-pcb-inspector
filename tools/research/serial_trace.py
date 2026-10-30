# -*- coding: utf-8 -*-
"""1) 读 ra_uart_ops 表；2) 连续命中 rt_serial_init，记录每个被打开的串口设备名"""
import sys
import time

from pyocd.core.helpers import ConnectHelper
from pyocd.core.target import Target

OPS = 0x0201C89C
SERIAL_INIT = 0x02013814


def main():
    with ConnectHelper.session_with_chosen_probe(target_override="r7ka8p1kf") as s:
        t = s.target
        t.halt()

        print("=== ra_uart_ops 表（5 个函数指针）===")
        raw = bytes(t.read_memory_block8(OPS, 20))
        for i, name in enumerate(("configure", "control", "putc", "getc", "transmit")):
            v = int.from_bytes(raw[i * 4:(i + 1) * 4], "little")
            print(f"  {name:10s} = 0x{v:08X}" + ("   <-- NULL!" if v == 0 else ""))

        print("=== 逐个捕获 rt_serial_init 的设备 ===")
        t.reset_and_halt()
        t.set_breakpoint(SERIAL_INIT)
        for n in range(6):
            t.resume()
            end = time.time() + 6
            while time.time() < end and t.get_state() != Target.State.HALTED:
                time.sleep(0.03)
            if t.get_state() != Target.State.HALTED:
                print(f"  [{n}] 无更多命中")
                break
            dev = t.read_core_register("r0")
            try:
                nm = bytes(t.read_memory_block8(dev, 8)).split(b"\x00")[0].decode("ascii", "replace")
            except Exception:
                nm = "<unreadable>"
            # 读该设备的 ops 指针（偏移 0x60，来自上一次 dump）
            try:
                ops = int.from_bytes(bytes(t.read_memory_block8(dev + 0x60, 4)), "little")
            except Exception:
                ops = 0
            print(f"  [{n}] dev=0x{dev:08X} name='{nm}' ops=0x{ops:08X}")
        t.remove_breakpoint(SERIAL_INIT)
        t.resume()
    return 0


if __name__ == "__main__":
    sys.exit(main())
