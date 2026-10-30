import numpy as np
from PIL import Image
im = Image.open(r"D:\RTT\_re\video3\f_36.png").convert("RGB")
# 面板区域（目测）
box = (370, 150, 1070, 580)
crop = im.crop(box)
crop = crop.resize((crop.width*2, crop.height*2), Image.NEAREST)
crop.save(r"D:\RTT\_re\shots\panel_zoom.png")
print("  裁剪已保存:", crop.size)
a = np.asarray(crop).astype(np.float32)
h,w,_ = a.shape
# 左下角区域（面板内左下）
q = a[int(h*0.72):int(h*0.95), int(w*0.02):int(w*0.22)]
print(f"  面板左下角 RGB = ({q[...,0].mean():.0f},{q[...,1].mean():.0f},{q[...,2].mean():.0f})")
q2 = a[int(h*0.72):int(h*0.95), int(w*0.78):int(w*0.98)]
print(f"  面板右下角 RGB = ({q2[...,0].mean():.0f},{q2[...,1].mean():.0f},{q2[...,2].mean():.0f})")
