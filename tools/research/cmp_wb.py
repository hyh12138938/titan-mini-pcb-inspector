import numpy as np
from PIL import Image
for name in ("awb_auto", "wb_fixed"):
    im = np.asarray(Image.open(rf"D:\RTT\_re\shots\{name}.png").convert("RGB")).astype(np.float32)
    r,g,b = im[...,0].mean(), im[...,1].mean(), im[...,2].mean()
    paper = im[380:430, 640:760, :].reshape(-1,3)
    pr,pg,pb = paper[:,0].mean(), paper[:,1].mean(), paper[:,2].mean()
    lum = np.asarray(Image.open(rf"D:\RTT\_re\shots\{name}.png").convert("L"), dtype=np.float32)
    print(f"  {name:10s} 全图 R={r:5.1f} G={g:5.1f} B={b:5.1f} G/R={g/r:4.2f}")
    print(f"  {'':10s} 白纸 R={pr:5.1f} G={pg:5.1f} B={pb:5.1f} G/R={pg/pr:4.2f} B/R={pb/pr:4.2f}  亮度={lum.mean():.1f}")
