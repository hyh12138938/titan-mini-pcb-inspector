import numpy as np
from PIL import Image
for name in ("pad_real", "pad_bright"):
    im = np.asarray(Image.open(rf"D:\RTT\_re\shots\{name}.png").convert("L"), dtype=np.float32)
    print(f"  {name:10s} 平均亮度={im.mean():6.2f}  P99={np.percentile(im,99):6.1f}  最亮={im.max():.0f}")
