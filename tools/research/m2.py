import numpy as np
from PIL import Image
g = np.asarray(Image.open(r"D:\RTT\_re\shots\dbuf0.png").convert("L"), dtype=np.float32)
col=g.mean(axis=0); c=col-col.mean(); ac=np.correlate(c,c,mode="full")[len(c)-1:]; ac/=(ac[0]+1e-6)
pk=int(np.argmax(ac[5:80])+5)
print(f"  亮度={g.mean():.1f} 对比度={g.std():.1f} 竖条周期={pk}px 相关度={ac[pk]:.2f}")
print(f"  左条={g[:,:70].mean():.1f} 右条={g[:,-70:].mean():.1f} 中间={g[:,100:700].mean():.1f}")
