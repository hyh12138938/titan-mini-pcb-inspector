import numpy as np
from PIL import Image
g = np.asarray(Image.open(r"D:\RTT\_re\shots\restored.png").convert("L"), dtype=np.float32)
# 取中间一片平坦区域，看 5px 周期的幅度
row0, row1 = 120, 200
patch = g[row0:row1, 300:460]
col = patch.mean(axis=0)
print("  列均值（x=300..459，每 10 列取一个）:")
print("   " + " ".join(f"{v:5.1f}" for v in col[::10]))
det = col - col.mean()
amp = det.max() - det.min()
print(f"  峰峰幅度 = {amp:.1f} (占满量程 {amp/255*100:.1f}%)")
# 逐列相邻差
d = np.abs(np.diff(col))
print(f"  相邻列平均跳变 = {d.mean():.2f}, 最大 = {d.max():.2f}")
