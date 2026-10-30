# -*- coding: utf-8 -*-
"""快速连拍：对候选缓冲做降采样读取，看哪块内容在变、亮度多少"""
import time

import numpy as np
from pyocd.core.helpers import ConnectHelper

W, H = 800, 480
CAND = {"plane0": 0x68096080, "plane1": 0x68151880}
STRIDE = 8          # 每 8 行取 1 行


def shot(t, base):
    rows = []
    for y in range(0, H, STRIDE):
        rows.append(bytes(t.read_memory_block8(base + y * W * 2, W * 2)))
    a = np.frombuffer(b"".join(rows), dtype="<u2").reshape(-1, W)
    r = ((a >> 11) & 0x1F).astype(np.float32) * 255 / 31
    g = ((a >> 5) & 0x3F).astype(np.float32) * 255 / 63
    b = (a & 0x1F).astype(np.float32) * 255 / 31
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    return lum.mean(), lum.max(), len(np.unique(a)), a


def main():
    with ConnectHelper.session_with_chosen_probe(target_override="r7ka8p1kf") as s:
        t = s.target
        for name, base in CAND.items():
            print(f"=== {name} @0x{base:08X} ===")
            for i in range(3):
                t.halt()
                m, mx, u, a = shot(t, base)
                t.resume()
                print(f"  [{i}] 平均亮度={m:6.2f} 最亮={mx:5.1f} 色数={u:5d}")
                time.sleep(0.35)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
