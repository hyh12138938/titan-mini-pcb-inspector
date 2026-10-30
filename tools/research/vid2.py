import glob, numpy as np
from PIL import Image
for f in sorted(glob.glob(r"D:\RTT\_re\video2\f_*.png"))[:12]:
    im = np.asarray(Image.open(f).convert("RGB")).astype(np.float32)
    h,w,_ = im.shape
    # 取画面中心区域（避开边框）
    c = im[int(h*0.35):int(h*0.65), int(w*0.25):int(w*0.75)]
    r,g,b = c[...,0].mean(), c[...,1].mean(), c[...,2].mean()
    print(f"  {f.split(chr(92))[-1]}: 中心 R={r:5.1f} G={g:5.1f} B={b:5.1f}")
