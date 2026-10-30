# -*- coding: utf-8 -*-
"""找到 main 线程对象，从其栈里恢复"卡住时的 PC"，定位阻塞函数"""
import sys
import time

from pyocd.core.helpers import ConnectHelper


def find_thread(t, name=b"main\x00"):
    for start, size in ((0x22020000, 0x60000),):
        try:
            d = bytes(t.read_memory_block8(start, size))
        except Exception:
            continue
        i = d.find(name)
        if i != -1:
            return start + i
    return None


def main():
    with ConnectHelper.session_with_chosen_probe(target_override="r7ka8p1kf") as s:
        t = s.target
        t.halt()
        thr = find_thread(t)
        if not thr:
            print("没找到 main 线程")
            t.resume()
            return 1
        print(f"main thread @0x{thr:08X}")
        sp = t.read32(thr + 24)
        print(f"  saved sp = 0x{sp:08X}")
        if not (0x22000000 <= sp <= 0x22180000):
            print("  sp 异常")
            t.resume()
            return 1
        words = [int.from_bytes(bytes(t.read_memory_block8(sp + i * 4, 4)), "little")
                 for i in range(40)]
        code = [(i, w) for i, w in enumerate(words) if 0x02000000 <= w < 0x02100000]
        print("  stack 中的代码地址:")
        for i, w in code[:10]:
            print(f"    [sp+{i*4:3d}] 0x{w:08X}")

        # BLOCKED 时 sp 指向 {r4-r11, exc_return} 或异常帧；尝试按异常帧解析
        # 常见布局：sp+0x00 r0, +4 r1, +8 r2, +12 r3, +16 r12, +20 lr, +24 pc, +28 xpsr
        for base in (0, 8, 16, 32):
            try:
                pc = int.from_bytes(bytes(t.read_memory_block8(sp + base + 24, 4)), "little")
                lr = int.from_bytes(bytes(t.read_memory_block8(sp + base + 20, 4)), "little")
                if 0x02000000 <= pc < 0x02100000:
                    print(f"  猜测帧基址 +{base}: lr=0x{lr:08X} pc=0x{pc:08X}")
            except Exception:
                pass
        t.resume()
    return 0


if __name__ == "__main__":
    sys.exit(main())
