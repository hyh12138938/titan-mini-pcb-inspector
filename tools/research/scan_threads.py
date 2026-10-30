# -*- coding: utf-8 -*-
"""在 RAM 里扫线程对象名，判断 main/tshell 线程是否存在"""
import sys

from pyocd.core.helpers import ConnectHelper

START = 0x22020000
SIZE = 0x60000      # 384 KB


def main():
    with ConnectHelper.session_with_chosen_probe(target_override="r7ka8p1kf") as s:
        t = s.target
        t.halt()
        try:
            data = bytes(t.read_memory_block8(START, SIZE))
        except Exception as e:
            print("读取失败:", e)
            t.resume()
            return 1
        for name in (b"main\x00", b"tshell\x00", b"idle\x00", b"tidle0\x00"):
            idx = data.find(name)
            hits = []
            while idx != -1 and len(hits) < 3:
                hits.append(START + idx)
                idx = data.find(name, idx + 1)
            print(f"  {name.decode(errors='replace'):10s} -> " +
                  (", ".join(f"0x{a:08X}" for a in hits) if hits else "未找到"))
        t.resume()
    return 0


if __name__ == "__main__":
    sys.exit(main())
