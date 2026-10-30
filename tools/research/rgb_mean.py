import numpy as np
from PIL import Image
for name in ("awb_auto", "bright2x", "b_plus3"):
    try:
        im = np.asarray(Image.open(rf"D:\RTT\_re\shots\{name}.png").convert("RGB")).astype(np.float32)
    except FileNotFoundError:
        continue
    r, g, b = im[...,0].mean(), im[...,1].mean(), im[...,2].mean()
    print(f"  {name:10s} R={r:6.1f} G={g:6.1f} B={b:6.1f}  G/R={g/r:5.2f} G/B={g/b:5.2f}")
