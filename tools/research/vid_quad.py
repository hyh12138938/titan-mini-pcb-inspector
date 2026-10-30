import numpy as np, glob
from PIL import Image
def quadrants(path):
    im = np.asarray(Image.open(path).convert("RGB")).astype(np.float32)
    # 面板大致范围（由 f_07 目测）
    x0,x1,y0,y1 = 480, 1080, 230, 500
    p = im[y0:y1, x0:x1]
    h,w,_ = p.shape
    def m(a): return a.reshape(-1,3).mean(axis=0)
    return (m(p[:h//2,:w//2]), m(p[:h//2,w//2:]), m(p[h//2:,:w//2]), m(p[h//2:,w//2:]))
for f in ["f_06","f_07","f_08","f_10","f_14","f_20","f_30"]:
    path = rf"D:\RTT\_re\video2\{f}.png"
    try:
        tl,tr,bl,br = quadrants(path)
    except FileNotFoundError:
        continue
    fmt = lambda a: f"({a[0]:3.0f},{a[1]:3.0f},{a[2]:3.0f})"
    print(f"  {f}: 左上{fmt(tl)} 右上{fmt(tr)} 左下{fmt(bl)} 右下{fmt(br)}")
