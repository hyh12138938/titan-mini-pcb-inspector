# -*- coding: utf-8 -*-
"""把照片里的面板内容与预期图案做 8 种变换匹配，给出唯一方向结论。"""
import numpy as np
from PIL import Image

PHOTO = r"C:\Users\hyh7758521\.dsh\attachments\v1\objects\cd\cd82a7eaf36f346ca92b17005787f28b1dbd4d37a57542935c4e56d7730ad32e"
CROP = (330, 310, 830, 1150)          # 面板内部（目测，含少量边框）

FB_W, FB_H = 800, 480


def expected():
    """按 hal_entry.c 里实际画的矩形，生成 3 类标签图: 0黑 1白(F) 2红 3绿"""
    e = np.zeros((FB_H, FB_W), np.int8)
    def rect(x, y, w, h, lab):
        e[max(0, y):y + h, max(0, x):x + w] = lab
    rect(100, 80, 70, 320, 1)             # F 竖笔画
    rect(170, 80, 240, 70, 1)             # F 上横
    rect(170, 200, 160, 70, 1)            # F 中横
    rect(FB_W - 90, 20, 70, 70, 2)        # 红标记（fb 右上）
    rect(20, FB_H - 90, 70, 70, 3)        # 绿标记（fb 左下）
    return e


def observed():
    im = Image.open(PHOTO).convert("RGB").crop(CROP)
    a = np.asarray(im).astype(np.float32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    lab = np.zeros(a.shape[:2], np.int8)
    lab[(r > 150) & (g > 150) & (b > 150)] = 1                       # 白
    lab[(r > 120) & (g < 110) & (b < 110)] = 2                       # 红
    lab[(g > 130) & (r < 140) & (b < 130) & (g > r + 30)] = 3        # 绿
    return lab


TRANSFORMS = {
    "原样":        lambda e: e,
    "旋转180":     lambda e: np.rot90(e, 2),
    "左右镜像":    lambda e: np.fliplr(e),
    "上下镜像":    lambda e: np.flipud(e),
    "旋转90逆":    lambda e: np.rot90(e, 1),
    "旋转90顺":    lambda e: np.rot90(e, 3),
    "转90逆+镜像": lambda e: np.fliplr(np.rot90(e, 1)),
    "转90顺+镜像": lambda e: np.fliplr(np.rot90(e, 3)),
}


def score(exp_lab, obs_small):
    """逐像素类别一致率（只统计非黑像素，避免大片黑底抬高分数）"""
    m = (exp_lab > 0) | (obs_small > 0)
    if m.sum() < 100:
        return 0.0
    return float((exp_lab[m] == obs_small[m]).mean())


def main():
    e = expected()
    obs = observed()
    print(f"  观测类别统计: 白={np.sum(obs==1)} 红={np.sum(obs==2)} 绿={np.sum(obs==3)} 黑={np.sum(obs==0)}")

    results = []
    for name, fn in TRANSFORMS.items():
        t = fn(e)
        # 把变换后的模板缩放到观测图像的尺寸
        ti = Image.fromarray(t.astype(np.uint8)).resize((obs.shape[1], obs.shape[0]), Image.NEAREST)
        tl = np.asarray(ti)
        s = score(tl, obs)
        results.append((s, name))

    results.sort(reverse=True)
    print("\n  匹配得分（越高越像）:")
    for s, name in results:
        print(f"    {name:12s} {s*100:5.1f}%")


if __name__ == "__main__":
    main()
