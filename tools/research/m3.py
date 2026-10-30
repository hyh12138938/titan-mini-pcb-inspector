import numpy as np
from PIL import Image
im = np.asarray(Image.open(r"D:\RTT\_re\shots\restored.png").convert("RGB")).astype(np.float32)
g  = np.asarray(Image.open(r"D:\RTT\_re\shots\restored.png").convert("L"), dtype=np.float32)
col=g.mean(axis=0); c=col-col.mean(); ac=np.correlate(c,c,mode="full")[len(c)-1:]; ac/=(ac[0]+1e-6)
pk=int(np.argmax(ac[5:80])+5)
flat=im.reshape(-1,3); over=(flat.mean(axis=1)>240).mean()*100
print(f"  亮度={g.mean():.1f} 对比度={g.std():.1f} 过曝={over:.1f}% 竖条周期={pk}px 相关={ac[pk]:.2f}")
print(f"  左右边缘亮度: 左={g[:,:40].mean():.1f} 右={g[:,-40:].mean():.1f}  (铺满整屏时应接近中间)")
