# -*- coding: utf-8 -*-
"""参数扫描：给若干组 (gain, gamma, contrast)，逐组 poke + 截图 + 量化，最后排序。

用法: python sweep.py --elf <elf> --crop 80,0,720,480
判据（越靠前权重越高）：
  1) 墙面中性 |G/R-1| 越小越好
  2) 削顶 <= 1.5%
  3) 平均亮度落在 125..155
  4) spread（p95-p5）越大越好
  5) 噪声 |dH| 越小越好
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
POKE = os.path.join(HERE, "poke.py")
SHOTS = os.path.join(HERE, "shots")

VARIANTS = [
    ("A_cur", 33, 28, 32, 88, 108),
    ("B_mid", 33, 28, 32, 84, 118),
    ("C_punch", 33, 28, 32, 80, 126),
    ("D_soft", 34, 28, 32, 92, 112),
]


def poke(elf, g):
    gr, gg, gb, gamma, contrast = g
    cmd = [sys.executable, POKE, "--elf", elf,
           f"s_gain_r={gr}", f"s_gain_g={gg}", f"s_gain_b={gb}",
           f"s_gamma={gamma}", f"s_contrast={contrast}", "s_dirty=1"]
    subprocess.run(cmd, capture_output=True, text=True)


def grab(elf, out):
    subprocess.run([sys.executable, GRAB, "--elf", elf, "--out", out,
                    "--index-sym", "s_disp_idx"], capture_output=True, text=True)


def metrics(png, crop):
    a = np.asarray(Image.open(png).convert("RGB")).astype(np.float32)
    x0, y0, x1, y1 = crop
    cam = a[y0:y1, x0:x1]
    y = 0.299 * cam[..., 0] + 0.587 * cam[..., 1] + 0.114 * cam[..., 2]
    wall = a[120:260, 260:520]
    wr, wg, wb = wall[..., 0].mean(), wall[..., 1].mean(), wall[..., 2].mean()
    mx = cam.max(axis=2)
    mn = cam.min(axis=2)
    return {
        "y": float(y.mean()),
        "spread": float(np.percentile(y, 95) - np.percentile(y, 5)),
        "white": float((y > 251).mean() * 100),
        "black": float((y < 4).mean() * 100),
        "noise": float(np.abs(np.diff(y, axis=1)).mean()),
        "wall_gr": float(wg / max(wr, 1e-3)),
        "wall_gb": float(wg / max(wb, 1e-3)),
        "sat": float(((mx - mn) / (mx + 1.0)).mean()),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--elf", required=True)
    ap.add_argument("--crop", default="80,0,720,480")
    a = ap.parse_args()
    crop = tuple(int(v) for v in a.crop.split(","))
    os.makedirs(SHOTS, exist_ok=True)

    rows = []
    for name, gr, gg, gb, gamma, contrast in VARIANTS:
        poke(a.elf, (gr, gg, gb, gamma, contrast))
        time.sleep(1.2)
        png = os.path.join(SHOTS, f"sweep_{name}.png")
        grab(a.elf, png)
        m = metrics(png, crop)
        m["name"] = name
        m["params"] = f"{gr}/{gg}/{gb} g{gamma} c{contrast}"
        rows.append(m)
        print(f"[{name}] {m['params']}  Y={m['y']:.1f} spread={m['spread']:.1f} "
              f"clipW={m['white']:.2f}% noise={m['noise']:.2f} "
              f"wall G/R={m['wall_gr']:.3f} G/B={m['wall_gb']:.3f} sat={m['sat']:.3f}")

    def score(m):
        s = 0.0
        s -= abs(m["wall_gr"] - 1.0) * 400          # 墙面中性最重要
        s -= abs(m["wall_gb"] - 1.0) * 200
        if m["white"] > 1.5:
            s -= (m["white"] - 1.5) * 6
        s -= abs(m["y"] - 140) * 0.6                # 目标亮度 140
        s += m["spread"] * 0.25
        s -= max(0.0, m["noise"] - 4.0) * 6
        return s

    print("\n=== 排序 ===")
    for m in sorted(rows, key=score, reverse=True):
        print(f"  {score(m):8.1f}  {m['name']:<8} {m['params']}")
    best = max(rows, key=score)
    print(f"\nBEST = {best['name']}  {best['params']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
