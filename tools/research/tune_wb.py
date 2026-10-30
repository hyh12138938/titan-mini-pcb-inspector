# -*- coding: utf-8 -*-
"""自动白平衡收敛：截图量 G/R、G/B，反解每通道增益，poke 进板子，再量。

用法:
  python tune_wb.py --elf <elf> [--iters 2] [--crop 80,0,720,480]

原理: 增益线性作用在像素值上，所以  new_gain = old_gain * (current_ratio)
      迭代两次即可把 G/R、G/B 压到 1.00 附近。
"""
import argparse
import os
import subprocess
import sys
import time

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
GRAB = os.path.join(HERE, "grab_fb.py")
PEEK = os.path.join(HERE, "poke.py")
SHOTS = os.path.join(HERE, "shots")


def grab(elf, out):
    subprocess.run([sys.executable, GRAB, "--elf", elf, "--out", out],
                   capture_output=True, text=True)
    return out


def measure(png, crop=None):
    a = np.asarray(Image.open(png).convert("RGB")).astype(np.float32)
    if crop:
        x0, y0, x1, y1 = crop
        a = a[y0:y1, x0:x1]
    r, g, b = a[..., 0].mean(), a[..., 1].mean(), a[..., 2].mean()
    y = (0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]).mean()
    return r, g, b, y


def peek_gains(elf):
    out = subprocess.run([sys.executable, PEEK, "--elf", elf, "--show",
                          "s_gain_r", "s_gain_g", "s_gain_b"],
                         capture_output=True, text=True).stdout
    vals = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 4 and parts[0] in ("s_gain_r", "s_gain_g", "s_gain_b"):
            vals[parts[0]] = int(line.rsplit("=", 1)[1])
    return vals


def poke_gains(elf, r, g, b):
    cmd = [sys.executable, PEEK, "--elf", elf,
           f"s_gain_r={r}", f"s_gain_g={g}", f"s_gain_b={b}", "s_dirty=1"]
    out = subprocess.run(cmd, capture_output=True, text=True)
    return out.stdout + out.stderr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--elf", required=True)
    ap.add_argument("--iters", type=int, default=2)
    ap.add_argument("--crop", default="80,0,720,480")
    a = ap.parse_args()

    crop = tuple(int(v) for v in a.crop.split(",")) if a.crop else None
    os.makedirs(SHOTS, exist_ok=True)

    for it in range(a.iters + 1):
        png = os.path.join(SHOTS, f"wb_it{it}.png")
        grab(a.elf, png)
        r, g, b, y = measure(png, crop)
        gr = g / r if r > 1e-3 else 0
        gb = g / b if b > 1e-3 else 0
        gains = peek_gains(a.elf)
        print(f"[it{it}] mean R={r:6.1f} G={g:6.1f} B={b:6.1f} Y={y:6.1f}  "
              f"G/R={gr:.3f} G/B={gb:.3f}  gains={gains}  ({png})")

        if it == a.iters:
            break

        if not gains:
            print("  !! 读不到增益，停止")
            break

        nr = int(round(gains["s_gain_r"] * gr))
        ng = gains["s_gain_g"]
        nb = int(round(gains["s_gain_b"] * gb))
        nr = max(1, min(60, nr))
        nb = max(1, min(60, nb))
        print(f"  -> poke gain {nr}/{ng}/{nb}")
        print("  " + poke_gains(a.elf, nr, ng, nb).replace("\n", "\n  "))
        time.sleep(1.5)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
