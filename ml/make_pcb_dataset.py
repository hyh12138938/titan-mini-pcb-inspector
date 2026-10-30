# -*- coding: utf-8 -*-
"""
DeepPCB -> 96x96 二分类数据集（good / defect）

思路：
    DeepPCB 每对图是"同一块板"的 (temp=有缺陷, test=无缺陷基准)，像素级对齐。
    对每对图：
      1. 算 |temp - test| 得到差异图
      2. 用 16x16 网格找差异能量最大的位置（= 缺陷所在）
      3. 在 temp 上裁 96x96 -> defect/
         在 test 上裁同一位置 -> good/
    这样 good/defect 的差异只来自"那个位置有没有缺陷"，
    和你板子上"焊盘有没有元件"是同构的问题。

输出：
    D:\\RTT\\ml\\data\\pcb_bin\\good\\*.jpg
    D:\\RTT\\ml\\data\\pcb_bin\\defect\\*.jpg
"""
import os
import random

import numpy as np
from PIL import Image

SRC = r"D:\RTT\ml\data\DeepPCB-master\PCBData"
DST = r"D:\RTT\ml\data\pcb_bin"
PATCH = 96
BLOCK = 16
PER_PAIR = 2          # 每对图产生几个样本（1 个缺陷位置 + 1 个随机位置）
MAX_PER_CLASS = 900   # 每类最多多少张


def blocks_energy(diff, bs=BLOCK):
    h, w = diff.shape
    hb, wb = h // bs, w // bs
    d = diff[:hb * bs, :wb * bs].reshape(hb, bs, wb, bs).astype(np.float32)
    return d.sum(axis=(1, 3))          # (hb, wb)


def crop(img_arr, cy, cx, size=PATCH):
    h, w = img_arr.shape
    half = size // 2
    y0 = min(max(cy - half, 0), h - size)
    x0 = min(max(cx - half, 0), w - size)
    return img_arr[y0:y0 + size, x0:x0 + size]


def main():
    random.seed(0)
    np.random.seed(0)
    for c in ("good", "defect"):
        os.makedirs(os.path.join(DST, c), exist_ok=True)

    pairs = []
    for root, _, files in os.walk(SRC):
        temps = [f for f in files if f.endswith("_temp.jpg")]
        for t in temps:
            te = t.replace("_temp.jpg", "_test.jpg")
            if os.path.exists(os.path.join(root, te)):
                pairs.append((os.path.join(root, t), os.path.join(root, te)))

    print(f"[输入] 找到 {len(pairs)} 对 (temp, test)")
    random.shuffle(pairs)

    n_good = n_def = 0
    idx = 0
    for tp, sp in pairs:
        if n_good >= MAX_PER_CLASS and n_def >= MAX_PER_CLASS:
            break
        try:
            ti = Image.open(tp).convert("L")
            si = Image.open(sp).convert("L")
        except Exception:
            continue
        ta = np.asarray(ti, dtype=np.int16)
        sa = np.asarray(si, dtype=np.int16)

        diff = np.abs(ta - sa)
        if diff.max() < 30:            # 这对基本没差异，跳过
            continue

        e = blocks_energy(diff)
        hb, wb = e.shape
        flat = np.argsort(e.ravel())[::-1][:PER_PAIR]
        for k, pos in enumerate(flat):
            by, bx = divmod(int(pos), wb)
            cy, cx = by * BLOCK + BLOCK // 2, bx * BLOCK + BLOCK // 2
            if k > 0 and random.random() < 0.5:
                continue               # 第二个位置有 50% 概率跳过，保持正负均衡

            if n_def < MAX_PER_CLASS:
                Image.fromarray(crop(ta, cy, cx).astype(np.uint8)).save(
                    os.path.join(DST, "defect", f"{idx:05d}.jpg"), quality=92)
                n_def += 1
            if n_good < MAX_PER_CLASS:
                Image.fromarray(crop(sa, cy, cx).astype(np.uint8)).save(
                    os.path.join(DST, "good", f"{idx:05d}g.jpg"), quality=92)
                n_good += 1
            idx += 1

    print(f"[完成] good={n_good}  defect={n_def}  -> {DST}")


if __name__ == "__main__":
    main()
