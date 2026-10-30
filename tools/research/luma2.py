import numpy as np
from PIL import Image
im = np.asarray(Image.open(r"D:\RTT\_re\shots\pad_fallback.png").convert("L"), dtype=np.float32)
a = np.asarray(Image.open(r"D:\RTT\_re\shots\pad_fallback.png"))
print(f"  mean={im.mean():.2f} max={im.max():.0f} 唯一色数={len(np.unique(a.reshape(-1,3),axis=0))}")
