import numpy as np
from PIL import Image
for name in ("wb_r38", "stretch", "stretch2"):
    im = np.asarray(Image.open(rf"D:\RTT\_re\shots\{name}.png").convert("RGB")).astype(np.float32)
    g = np.asarray(Image.open(rf"D:\RTT\_re\shots\{name}.png").convert("L"), dtype=np.float32)
    flat = im.reshape(-1,3)
    over = (flat.mean(axis=1) > 240).mean()*100
    print(f"  {name:9s} 亮度={g.mean():5.1f} 对比度={g.std():5.1f} 过曝={over:4.1f}%")
