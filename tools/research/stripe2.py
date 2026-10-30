import numpy as np
from PIL import Image
im = np.asarray(Image.open(r"D:\RTT\_re\shots\one2one.png").convert("RGB")).astype(np.float32)
g  = np.asarray(Image.open(r"D:\RTT\_re\shots\one2one.png").convert("L"), dtype=np.float32)
col = g.mean(axis=0)
c = col - col.mean(); ac = np.correlate(c, c, mode="full")[len(c)-1:]; ac /= (ac[0]+1e-6)
peak = int(np.argmax(ac[5:80]) + 5)
print(f"  亮度={g.mean():.1f} 对比度={g.std():.1f}")
print(f"  列自相关最强周期={peak}px 相关度={ac[peak]:.2f}   (修之前是 5px/0.90)")
# 检查左右是否有黑边（1:1 居中后 x<80 和 x>720 应为纯黑）
left = g[:, :70].mean(); right = g[:, -70:].mean(); mid = g[:, 100:700].mean()
print(f"  左边条亮度={left:.1f} 右边条亮度={right:.1f} 中间画面亮度={mid:.1f}")
