import numpy as np
from PIL import Image
im = np.asarray(Image.open(r"D:\RTT\_re\shots\awb_auto.png").convert("RGB"))
# 左下角方块：x 20..90, y (480-90)..(480-20)
patch = im[480-90:480-20, 20:90, :]
mean = patch.reshape(-1,3).mean(axis=0)
print(f"  方块平均 RGB = ({mean[0]:.0f}, {mean[1]:.0f}, {mean[2]:.0f})")
r,g,b = mean
if r > 120 and g < 100 and b < 100:
    print("  => 红色：判定为 检测到焊盘 (PAD)")
elif abs(r-g) < 30 and abs(g-b) < 30 and 90 < r < 190:
    print("  => 灰色：判定为 没有焊盘 (NO_PAD)")
else:
    print("  => 其它颜色")
# 顺带算整幅亮度
lum = np.asarray(Image.open(r"D:\RTT\_re\shots\awb_auto.png").convert("L"), dtype=np.float32)
print(f"  整幅平均亮度 = {lum.mean():.1f}")
