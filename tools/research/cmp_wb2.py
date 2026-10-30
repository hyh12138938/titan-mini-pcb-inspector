import numpy as np
from PIL import Image
for name in ("wb_fixed", "wb_r38"):
    im = np.asarray(Image.open(rf"D:\RTT\_re\shots\{name}.png").convert("RGB")).astype(np.float32)
    lum = np.asarray(Image.open(rf"D:\RTT\_re\shots\{name}.png").convert("L"), dtype=np.float32)
    flat = im.reshape(-1,3)
    bright = flat[flat.mean(axis=1) > 200]          # 白纸/高光
    r,g,b = flat[:,0].mean(), flat[:,1].mean(), flat[:,2].mean()
    br,bg,bb = bright[:,0].mean(), bright[:,1].mean(), bright[:,2].mean()
    print(f"  {name:10s} 全图 G/R={g/r:4.2f} | 亮部 G/R={bg/br:4.2f} B/R={bb/br:4.2f} | 亮度={lum.mean():5.1f}")
