# -*- coding: utf-8 -*-
"""往三个候选帧缓冲地址各画一条不同颜色的横带，用颜色反推"哪块才是屏上真实内容" """
import sys

from pyocd.core.helpers import ConnectHelper

W = 800
CANDS = [
    ("plane0_0x68096080", 0x68096080, 0xF800, 0,   80),    # 红：第 0-80 行
    ("plane1_0x68151880", 0x68151880, 0x07E0, 160, 240),   # 绿：第 160-240 行
    ("old_0x681C2000",    0x681C2000, 0x001F, 320, 400),   # 蓝：第 320-400 行
]


def main():
    with ConnectHelper.session_with_chosen_probe(target_override="r7ka8p1kf") as s:
        t = s.target
        t.halt()
        for name, base, color, y0, y1 in CANDS:
            line = color.to_bytes(2, "little") * W
            for y in range(y0, y1):
                t.write_memory_block8(base + y * W * 2, line)
            print(f"  {name}: 第 {y0}-{y1} 行 = 0x{color:04X}")
        t.resume()
    return 0


if __name__ == "__main__":
    sys.exit(main())
