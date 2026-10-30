# -*- coding: utf-8 -*-
"""量化分析帧缓冲截图：亮度、对比度、色偏、噪点、裁剪、暗角。

用法: python lcd_analyze.py <shot.png> [--ref <photo.jpg>]
输出一行 JSON + 人类可读摘要，便于迭代时比较版本。
"""
import argparse
import json
import sys

import numpy as np
from PIL import Image


def load(path):
    im = Image.open(path).convert("RGB")
    a = np.asarray(im).astype(np.float32)
    return a


def stats(a, tag=""):
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    # Rec.601 luma
    y = 0.299 * r + 0.587 * g + 0.114 * b

    mr, mg, mb = r.mean(), g.mean(), b.mean()
    my = y.mean()

    # contrast: percentile spread + std
    p5, p50, p95 = np.percentile(y, [5, 50, 95])
    spread = p95 - p5

    # colour cast: neutral grey has G/R == G/B == 1
    gr = mg / mr if mr > 1e-3 else 0.0
    gb = mg / mb if mb > 1e-3 else 0.0

    # saturation: mean (max-min) / (max+eps)
    mx = a.max(axis=2)
    mn = a.min(axis=2)
    sat = float(((mx - mn) / (mx + 1.0)).mean())

    # noise proxy: mean |horizontal difference| (structure also contributes,
    # so compare it between versions rather than against an absolute limit)
    dh = np.abs(np.diff(y, axis=1)).mean()
    dv = np.abs(np.diff(y, axis=0)).mean()

    # clipping
    black = float((y < 4).mean() * 100)
    white = float((y > 251).mean() * 100)

    # quadrant means (vignetting / one-sided gradient)
    h, w = y.shape
    q = [
        y[: h // 2, : w // 2].mean(),
        y[: h // 2, w // 2:].mean(),
        y[h // 2:, : w // 2].mean(),
        y[h // 2:, w // 2:].mean(),
    ]

    d = {
        "tag": tag,
        "shape": [int(h), int(w)],
        "mean_rgb": [round(float(mr), 1), round(float(mg), 1), round(float(mb), 1)],
        "mean_y": round(float(my), 1),
        "median_y": round(float(p50), 1),
        "p5": round(float(p5), 1),
        "p95": round(float(p95), 1),
        "spread": round(float(spread), 1),
        "std_y": round(float(y.std()), 1),
        "g_over_r": round(float(gr), 3),
        "g_over_b": round(float(gb), 3),
        "sat": round(sat, 3),
        "noise_h": round(float(dh), 2),
        "noise_v": round(float(dv), 2),
        "clip_black_pct": round(black, 2),
        "clip_white_pct": round(white, 2),
        "quadrants": [round(float(v), 1) for v in q],
    }
    return d


def verdict(d):
    """给出版本优劣的判据（越靠前越重要）。"""
    v = []
    if d["mean_y"] < 40:
        v.append("TOO_DARK")
    if d["mean_y"] > 175:
        v.append("TOO_BRIGHT")
    if d["spread"] < 70:
        v.append("LOW_CONTRAST")
    if d["g_over_r"] > 1.10 or d["g_over_b"] > 1.10:
        v.append("GREEN_CAST")
    if d["g_over_r"] < 0.90 or d["g_over_b"] < 0.90:
        v.append("MAGENTA_CAST")
    if d["sat"] < 0.10:
        v.append("WASHED_OUT")
    if d["clip_white_pct"] > 8:
        v.append("HIGHLIGHT_CLIP")
    if d["clip_black_pct"] > 8:
        v.append("SHADOW_CLIP")
    q = d["quadrants"]
    if q and (max(q) - min(q) > 40):
        v.append("UNEVEN")
    return v or ["OK"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("png")
    ap.add_argument("--tag", default="")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    img = load(a.png)
    d = stats(img, a.tag or a.png)
    d["verdict"] = verdict(d)

    if a.json:
        print(json.dumps(d, ensure_ascii=False))
        return 0

    print(f"[{d['tag']}]  {d['shape'][1]}x{d['shape'][0]}")
    print(f"  mean RGB      R={d['mean_rgb'][0]:6.1f}  G={d['mean_rgb'][1]:6.1f}  B={d['mean_rgb'][2]:6.1f}")
    print(f"  luma          mean={d['mean_y']:6.1f}  median={d['median_y']:6.1f}  "
          f"p5={d['p5']:5.1f}  p95={d['p95']:5.1f}")
    print(f"  contrast      spread={d['spread']:6.1f}  std={d['std_y']:5.1f}")
    print(f"  colour cast   G/R={d['g_over_r']:.3f}  G/B={d['g_over_b']:.3f}  sat={d['sat']:.3f}")
    print(f"  noise         |dH|={d['noise_h']:.2f}  |dV|={d['noise_v']:.2f}")
    print(f"  clipping      black={d['clip_black_pct']:.2f}%  white={d['clip_white_pct']:.2f}%")
    print(f"  quadrants     TL={d['quadrants'][0]:.1f} TR={d['quadrants'][1]:.1f} "
          f"BL={d['quadrants'][2]:.1f} BR={d['quadrants'][3]:.1f}")
    print(f"  verdict       {' '.join(d['verdict'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
