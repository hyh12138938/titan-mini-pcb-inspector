# -*- coding: utf-8 -*-
"""
用用户自己的 44 张洞洞板照片，构建"有焊盘 / 无焊盘"二分类数据集。

正样本（pad）   : 数据集里已裁好的 14,151 张空焊盘图，直接复用
负样本（no_pad）: 从**同一批原图**上、远离任何焊盘中心的位置裁同样大小的块
                  -> 绿油板面/板边，光照视角与正样本完全一致

输出：
    D:\\RTT\\ml\\data\\pad_user\\pad\\*.jpg
    D:\\RTT\\ml\\data\\pad_user\\no_pad\\*.jpg
"""
import csv
import os
import random
import shutil
from collections import defaultdict

from PIL import Image

DS = r"D:\RTT\数据集"
ORIG = r"C:\Users\hyh7758521\Downloads\IMG_20261020_214748_1等44项文件"
OUT = r"D:\RTT\ml\data\pad_user"
MAX_NEG_PER_PHOTO = 200


def main():
    for c in ("pad", "no_pad"):
        os.makedirs(os.path.join(OUT, c), exist_ok=True)

    rows = []
    with open(os.path.join(DS, "manifest.csv"), encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            rows.append(r)

    by_photo = defaultdict(list)
    for r in rows:
        by_photo[r["source_photo"]].append(r)

    print(f"[manifest] {len(rows)} 行, {len(by_photo)} 张原图")

    # ---- 1) 正样本：直接复用裁图 ----
    n_pad = 0
    for r in rows:
        src = os.path.join(DS, r["folder"], r["file"])
        if not os.path.exists(src):
            continue
        dst = os.path.join(OUT, "pad", f"{r['folder'][:2]}_{r['file']}")
        if not os.path.exists(dst):
            shutil.copyfile(src, dst)
        n_pad += 1
    print(f"[pad] {n_pad} 张")

    # ---- 2) 负样本：同图上远离焊盘的位置 ----
    random.seed(1234)
    n_neg = 0
    for photo, rs in by_photo.items():
        p = os.path.join(ORIG, photo)
        if not os.path.exists(p):
            # 原图可能改过名，尝试模糊匹配
            cand = [f for f in os.listdir(ORIG) if f.startswith(photo[:18])] if os.path.isdir(ORIG) else []
            if not cand:
                continue
            p = os.path.join(ORIG, cand[0])
        img = Image.open(p).convert("RGB")
        W, H = img.size

        centers = [(float(r["center_x"]), float(r["center_y"])) for r in rs]
        pitches = [float(r["pitch_px"]) for r in rs if r["pitch_px"]]
        crop_px = int(float(rs[0]["crop_px"]))
        pitch = sorted(pitches)[len(pitches) // 2] if pitches else 115.0
        min_d = pitch * 0.85
        half = crop_px // 2

        got = 0
        tries = 0
        while got < MAX_NEG_PER_PHOTO and tries < MAX_NEG_PER_PHOTO * 40:
            tries += 1
            x = random.randint(half, W - half - 1)
            y = random.randint(half, H - half - 1)
            if any((x - cx) ** 2 + (y - cy) ** 2 < min_d ** 2 for cx, cy in centers):
                continue
            box = (x - half, y - half, x - half + crop_px, y - half + crop_px)
            crop = img.crop(box)
            name = f"{os.path.splitext(photo)[0]}_{got:04d}.jpg"
            crop.save(os.path.join(OUT, "no_pad", name), quality=92)
            got += 1
        n_neg += got
        print(f"  {photo}: pads={len(centers)} pitch={pitch:.0f} neg={got}")

    print(f"[no_pad] {n_neg} 张")
    print(f"[输出] {OUT}")


if __name__ == "__main__":
    main()
