import numpy as np, time
from PIL import Image
from pyocd.core.helpers import ConnectHelper
W,H = 800,480
BASE = 0x68096080
def grab():
    with ConnectHelper.session_with_chosen_probe(target_override="r7ka8p1kf", frequency=1000000) as s:
        t=s.target; t.halt()
        rows=[]
        for y in range(H):
            for attempt in range(3):
                try:
                    rows.append(bytes(t.read_memory_block8(BASE+y*W*2, W*2))); break
                except Exception:
                    time.sleep(0.05); rows.append(b"\x00\x00"*W)
        t.resume()
    return np.frombuffer(b"".join(rows),dtype="<u2").reshape(H,W)
a = grab()
r=((a>>11)&0x1F)*255//31; g=((a>>5)&0x3F)*255//63; b=(a&0x1F)*255//31
img=Image.fromarray(np.dstack([r,g,b]).astype(np.uint8),"RGB")
img.save(r"D:\RTT\_re\shots\after_rot.png")
img.rotate(180).save(r"D:\RTT\_re\shots\after_rot_upright.png")
lum=np.asarray(img.convert("L"),dtype=np.float32)
print(f"  亮度={lum.mean():.1f} 色数={len(np.unique(a))}")
# 找状态方块：扫描 70x70 均匀块
best=None
for y in range(0,H-70,10):
    for x in range(0,W-70,10):
        p=a[y:y+70, x:x+70]
        if p.std() < 30:
            m=p.mean()
            if 0x8410-0x0600 < m < 0x8410+0x0600:
                best=(x,y,float(m),float(p.std()))
print("  均匀灰色方块:", best)
