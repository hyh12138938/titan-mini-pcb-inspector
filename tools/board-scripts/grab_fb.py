# -*- coding: utf-8 -*-
"""
从板子截屏（ELF 自适应版）：自动从固件 ELF 里解析 fb_background 的地址，
再用 pyocd 读回 RGB565 帧缓冲转 PNG。

用法：
    python grab_fb.py --elf <rtthread.elf> [--out shot.png]
"""
import argparse
import datetime
import os
import re
import subprocess
import time

import numpy as np
from pyocd.core.helpers import ConnectHelper
from PIL import Image

NM = r"D:\tools\arm-gnu-toolchain-13.3.rel1-mingw-w64-i686-arm-none-eabi\bin\arm-none-eabi-nm.exe"
W, H = 800, 480
OUT_DIR = r"D:\RTT\_re\shots"


def sym_addr(elf, name):
    out = subprocess.run([NM, elf], capture_output=True, text=True, errors="replace").stdout
    m = re.search(rf"^([0-9a-fA-F]{{8}})\s+\w\s+{re.escape(name)}$", out, re.M)
    return int(m.group(1), 16) if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--elf", required=True)
    ap.add_argument("--out")
    ap.add_argument("--addr-sym", default=None,
                    help="直接用这个符号的值当 framebuffer 地址（三缓冲时用）")
    ap.add_argument("--index-sym", default=None,
                    help="双缓冲：用这个符号的值(0/1)选要读的 framebuffer 块")
    a = ap.parse_args()

    fb = sym_addr(a.elf, "fb_background")
    if fb is None:
        print("!! ELF 里没找到 fb_background")
        return 1

    os.makedirs(OUT_DIR, exist_ok=True)
    out = a.out or os.path.join(
        OUT_DIR, "shot_" + datetime.datetime.now().strftime("%H%M%S") + ".png")

    with ConnectHelper.session_with_chosen_probe(target_override="r7ka8p1kf") as s:
        t = s.target
        t.halt()
        idx = 0
        if a.index_sym:
            ia = sym_addr(a.elf, a.index_sym)
            if ia is not None:
                idx = int.from_bytes(bytes(t.read_memory_block8(ia, 4)), "little") & 1
        if a.addr_sym:
            pa = sym_addr(a.elf, a.addr_sym)
            if pa is not None:
                fb = int.from_bytes(bytes(t.read_memory_block8(pa, 4)), "little")
        base = fb + idx * W * H * 2
        t0 = time.time()
        raw = bytes(t.read_memory_block8(base, W * H * 2))
        dt = time.time() - t0
        t.resume()

    arr = np.frombuffer(raw, dtype="<u2").reshape(H, W)
    r = ((arr >> 11) & 0x1F) * 255 // 31
    g = ((arr >> 5) & 0x3F) * 255 // 63
    b = (arr & 0x1F) * 255 // 31
    Image.fromarray(np.dstack([r, g, b]).astype(np.uint8), "RGB").save(out)

    uniq = np.unique(arr)
    print(f"fb_background = 0x{fb:08X}  读取 {W*H*2/1024:.0f} KB / {dt:.2f}s")
    print(f"不同像素值 {len(uniq)} 个，样例 {[hex(int(v)) for v in uniq[:6]]}")
    print(f"saved: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
