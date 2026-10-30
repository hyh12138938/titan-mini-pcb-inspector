import numpy as np
from PIL import Image
for n in ("final","final2"):
    try:
        g = np.asarray(Image.open(rf"D:\RTT\_re\shots\{n}.png").convert("L"), dtype=np.float32)
        print(f"  {n}: 亮度={g.mean():.1f} 最亮={g.max():.0f}")
    except FileNotFoundError:
        pass
