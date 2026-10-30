import numpy as np
from PIL import Image
from pyocd.core.helpers import ConnectHelper
W,H = 800,480
BASE = 0x68096080
with ConnectHelper.session_with_chosen_probe(target_override="r7ka8p1kf", frequency=1000000) as s:
    t=s.target; t.halt()
    rows=[]
    for y in range(0,H,4):
        rows.append(bytes(t.read_memory_block8(BASE+y*W*2, W*2)))
    t.resume()
a=np.frombuffer(b"".join(rows),dtype="<u2").reshape(-1,W)
r=((a>>11)&0x1F)*255//31; g=((a>>5)&0x3F)*255//63; b=(a&0x1F)*255//31
img=Image.fromarray(np.dstack([r,g,b]).astype(np.uint8),"RGB")
img.save(r"D:\RTT\_re\shots\rot_raw.png")
img.rotate(180).save(r"D:\RTT\_re\shots\rot_upright.png")
lum=np.asarray(img.convert("L"),dtype=np.float32)
print(f"  抓取完成: 亮度={lum.mean():.1f} 色数={len(np.unique(a))}")
