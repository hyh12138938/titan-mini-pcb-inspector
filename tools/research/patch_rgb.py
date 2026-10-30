import numpy as np
from PIL import Image
im = np.asarray(Image.open(r"D:\RTT\_re\shots\awb_auto.png").convert("RGB")).astype(np.float32)
patches = {
    "右下白纸":   (380, 430, 640, 760),
    "中部垫子":   (200, 260, 150, 600),
    "左上暗区":   (20, 60, 20, 200),
    "白框线":     None,
}
for name, box in patches.items():
    if box is None: continue
    y0,y1,x0,x1 = box
    p = im[y0:y1, x0:x1, :].reshape(-1,3)
    r,g,b = p[:,0].mean(), p[:,1].mean(), p[:,2].mean()
    print(f"  {name:8s} R={r:6.1f} G={g:6.1f} B={b:6.1f}   G/R={g/max(r,1):5.2f} B/R={b/max(r,1):5.2f}")
# 白框本身：找最亮的像素（白色 = 255,255,255 画上去的）
flat = im.reshape(-1,3)
bright = flat[flat.mean(axis=1) > 200]
if len(bright):
    r,g,b = bright[:,0].mean(), bright[:,1].mean(), bright[:,2].mean()
    print(f"  最亮像素集 R={r:6.1f} G={g:6.1f} B={b:6.1f}  (白框应接近 255,255,255)")
