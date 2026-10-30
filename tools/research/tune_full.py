# -*- coding: utf-8 -*-
"""一次性把显示参数算对：恒等 LUT 量原始画面 -> 灰世界白平衡 + p99 定增益。

流程
  1) poke 恒等 LUT（gain=16/16/16, black=0, gamma=100, contrast=100）
  2) 截图：此时 framebuffer 就等于相机原始 5/6/5 画面
  3) 在相机区域内算：
       - 未削顶像素上的逐通道均值（灰世界假设：场景平均应为中性）
       - 逐通道 p99（用来定总增益，留 headroom 防止削顶）
  4) 解出 gain_r/gain_g/gain_b（/16），poke 进去并重建
  5) 截图并打印结果，供人眼复核
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

# 5/6/5 -> 0..255 的最大值
MAXR = 31.0
MAXG = 63.0
MAXB = 31.0


def grab(elf, out):
    subprocess.run([sys.executable, GRAB, "--elf", elf, "--out", out],
                   capture_output=True, text=True)
    return out


def poke(elf, **kw):
    cmd = [sys.executable, POKE, "--elf", elf] + [f"{k}={v}" for k, v in kw.items()]
    out = subprocess.run(cmd, capture_output=True, text=True)
    txt = out.stdout + out.stderr
    bad = [l for l in txt.splitlines() if "MISMATCH" in l or "not found" in l]
    return bad, txt


def read_fb(png, crop):
    a = np.asarray(Image.open(png).convert("RGB")).astype(np.float32)
    x0, y0, x1, y1 = crop
    a = a[y0:y1, x0:x1]
    # 回到 5/6/5 原始量化域（截图是 8bit 扩展过的）
    r = a[..., 0] * MAXR / 255.0
    g = a[..., 1] * MAXG / 255.0
    b = a[..., 2] * MAXB / 255.0
    return r, g, b


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--elf", required=True)
    ap.add_argument("--crop", default="80,0,720,480")
    ap.add_argument("--headroom", type=float, default=0.94,
                    help="p99 映射到满量程的比例，<1 留余量防止削顶")
    a = ap.parse_args()

    crop = tuple(int(v) for v in a.crop.split(","))
    os.makedirs(SHOTS, exist_ok=True)

    # 1) 恒等 LUT
    bad, _ = poke(a.elf, s_gain_r=16, s_gain_g=16, s_gain_b=16,
                  s_black_r=0, s_black_g=0, s_black_b=0,
                  s_gamma=100, s_contrast=100, s_dirty=1)
    if bad:
        print("poke failed:", bad)
        return 2
    time.sleep(1.5)

    # 2) 原始画面
    raw_png = os.path.join(SHOTS, "tune_raw.png")
    grab(a.elf, raw_png)
    r, g, b = read_fb(raw_png, crop)

    # 3) 只在"没有削顶"的像素上统计，避免灯的饱和区污染灰世界
    notclip = (r < MAXR - 1.5) & (g < MAXG - 3.0) & (b < MAXB - 1.5)
    lit = notclip & ((r / MAXR + g / MAXG + b / MAXB) / 3.0 > 0.10)   # 丢掉纯黑背景
    m = lit if lit.sum() > 1000 else notclip

    mr, mg, mb = r[m].mean(), g[m].mean(), b[m].mean()
    p99r, p99g, p99b = np.percentile(r[m], 99), np.percentile(g[m], 99), np.percentile(b[m], 99)

    # 关键：三个通道满量程不同（31/63/31），必须先归一化再比较，否则比例全错
    nr, ng, nb = mr / MAXR, mg / MAXG, mb / MAXB
    pr, pg, pb = p99r / MAXR, p99g / MAXG, p99b / MAXB

    print(f"[raw] pixels used = {m.sum()} / {r.size}  ({m.sum()*100.0/r.size:.1f}%)")
    print(f"[raw] mean  R={mr:.2f}/31={nr:.3f}  G={mg:.2f}/63={ng:.3f}  B={mb:.2f}/31={nb:.3f}")
    print(f"[raw] p99   R={p99r:.2f}/31={pr:.3f}  G={p99g:.2f}/63={pg:.3f}  B={p99b:.2f}/31={pb:.3f}")

    # 4) 灰世界（归一化域）：让三通道均值相等；再统一缩放到 headroom
    wb_r = ng / nr if nr > 1e-3 else 1.0
    wb_b = ng / nb if nb > 1e-3 else 1.0

    # 归一化增益（相对，gain_g = k）
    gr, gg, gb = wb_r, 1.0, wb_b

    # 每个通道 p99 在增益后的相对亮度
    eff_r = pr * gr
    eff_g = pg * gg
    eff_b = pb * gb
    eff = max(eff_r, eff_g, eff_b)

    k = a.headroom / eff if eff > 1e-6 else 1.0

    gain_r = gr * k * 16.0
    gain_g = gg * k * 16.0
    gain_b = gb * k * 16.0

    gain_r = max(1, min(62, int(round(gain_r))))
    gain_g = max(1, min(62, int(round(gain_g))))
    gain_b = max(1, min(62, int(round(gain_b))))

    print(f"[solve] wb G/R={wb_r:.3f} G/B={wb_b:.3f}  global k={k:.3f}")
    print(f"[solve] gain = {gain_r}/{gain_g}/{gain_b}  (/16)")

    bad, _ = poke(a.elf, s_gain_r=gain_r, s_gain_g=gain_g, s_gain_b=gain_b, s_dirty=1)
    if bad:
        print("poke failed:", bad)
        return 2

    time.sleep(1.5)

    # 5) 复核
    out_png = os.path.join(SHOTS, "tune_out.png")
    grab(a.elf, out_png)
    r2, g2, b2 = read_fb(out_png, crop)
    y2 = 0.299 * r2 / MAXR + 0.587 * g2 / MAXG + 0.114 * b2 / MAXB
    print(f"[out] mean R={r2.mean()*255/MAXR:6.1f} G={g2.mean()*255/MAXG:6.1f} "
          f"B={b2.mean()*255/MAXB:6.1f}  Y={y2.mean()*255:6.1f}")
    print(f"[out] G/R={g2.mean()/max(r2.mean(),1e-3):.3f} G/B={g2.mean()/max(b2.mean(),1e-3):.3f}")
    print(f"[out] clip white={(y2>0.98).mean()*100:.2f}%  black={(y2<0.02).mean()*100:.2f}%")
    print(f"[out] {out_png}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
