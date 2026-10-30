import numpy as np
from PIL import Image
im = np.asarray(Image.open(r"D:\RTT\_re\shots\live.png").convert("RGB")).astype(np.float32)
g = np.asarray(Image.open(r"D:\RTT\_re\shots\live.png").convert("L"), dtype=np.float32)
# 竖条纹检测：列均值的相邻差
col = g.mean(axis=0)
d = np.abs(np.diff(col))
print(f"  亮度={g.mean():.1f} 对比度={g.std():.1f} 列均值相邻差 均值={d.mean():.2f} 最大={d.max():.2f}")
# 周期性：列均值的自相关峰值
c = col - col.mean()
ac = np.correlate(c, c, mode="full")[len(c)-1:]
ac = ac / (ac[0] + 1e-6)
peak = int(np.argmax(ac[5:80]) + 5)
print(f"  列方向自相关最强周期 ≈ {peak} px (值 {ac[peak]:.2f})")
