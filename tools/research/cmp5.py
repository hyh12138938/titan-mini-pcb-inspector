import numpy as np
from PIL import Image
im = np.asarray(Image.open(r"D:\RTT\_re\shots\final.png").convert("RGB")).astype(np.float32)
g = np.asarray(Image.open(r"D:\RTT\_re\shots\final.png").convert("L"), dtype=np.float32)
flat = im.reshape(-1,3)
over = (flat.mean(axis=1) > 240).mean()*100
bright = flat[flat.mean(axis=1) > 170]
r,gg,b = flat[:,0].mean(), flat[:,1].mean(), flat[:,2].mean()
print(f"  final     亮度={g.mean():5.1f} 对比度={g.std():5.1f} 过曝={over:4.1f}% 全图G/R={gg/r:4.2f}")
if len(bright):
    br,bg,bb = bright[:,0].mean(), bright[:,1].mean(), bright[:,2].mean()
    print(f"  亮部      R={br:5.1f} G={bg:5.1f} B={bb:5.1f}  G/R={bg/br:4.2f} B/R={bb/br:4.2f}")
