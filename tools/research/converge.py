import time
import numpy as np
from pyocd.core.helpers import ConnectHelper
W,H = 800,480
BASE = 0x68096080
def shot(t):
    rows=[bytes(t.read_memory_block8(BASE+y*W*2, W*2)) for y in range(0,H,8)]
    a=np.frombuffer(b"".join(rows),dtype="<u2").reshape(-1,W)
    r=((a>>11)&0x1F).astype(np.float32)*255/31
    g=((a>>5)&0x3F).astype(np.float32)*255/63
    b=(a&0x1F).astype(np.float32)*255/31
    lum=0.299*r+0.587*g+0.114*b
    return lum.mean(), len(np.unique(a))
with ConnectHelper.session_with_chosen_probe(target_override="r7ka8p1kf") as s:
    t=s.target
    for i in range(6):
        t.halt(); m,u=shot(t); t.resume()
        print(f"  t={i*2}s 平均亮度={m:6.2f} 色数={u}")
        time.sleep(2)
