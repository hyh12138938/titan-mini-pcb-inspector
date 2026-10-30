# -*- coding: utf-8 -*-
"""直接往帧缓冲写色块，验证 GLCDC 扫描输出是否正常"""
import sys

from pyocd.core.helpers import ConnectHelper

FB = 0x681C2000
W, H = 800, 480

COLORS = {
    "red":    0xF800,
    "green":  0x07E0,
    "blue":   0x001F,
    "white":  0xFFFF,
    "yellow": 0xFFE0,
}


def main():
    color = COLORS.get(sys.argv[1] if len(sys.argv) > 1 else "red", 0xF800)
    rows = int(sys.argv[2]) if len(sys.argv) > 2 else 120

    with ConnectHelper.session_with_chosen_probe(target_override="r7ka8p1kf") as s:
        t = s.target
        t.halt()
        line = color.to_bytes(2, "little") * W
        for y in range(rows):
            t.write_memory_block8(FB + y * W * 2, line)
        print(f"已写入 {rows} 行 颜色=0x{color:04X} 到 0x{FB:08X}")
        # 读回前 8 个像素确认
        d = bytes(t.read_memory_block8(FB, 16))
        print("回读:", d.hex(" "))
        t.resume()
    return 0


if __name__ == "__main__":
    sys.exit(main())
