import numpy as np, time
from pyocd.core.helpers import ConnectHelper
from PIL import Image
W,H,PLANE = 800,480,800*480*2
base = 0x68096080
def sample(t, addr):
    rows=[bytes(t.read_memory_block8(addr+y*W*2, W*2)) for y in range(0,H,8)]
    a=np.frombuffer(b"".join(rows),dtype="<u2")
    return len(np.unique(a)), float(a.mean())
with ConnectHelper.session_with_chosen_probe(target_override="r7ka8p1kf") as s:
    t=s.target
    best=None
    for name,addr in (("plane0",base),("plane1",base+PLANE)):
        t.halt(); u,m1=sample(t,addr); t.resume(); time.sleep(0.3)
        t.halt(); _,m2=sample(t,addr); t.resume()
        live = abs(m1-m2) > 0.05
        print(f"  {name} 色数={u:5d} 亮度={m1:6.2f} 变化={'是' if live else '否'}")
        if best is None or u > best[1]: best=(name,addr,u)
    name,addr,_ = best
    print(f"  -> 采用 {name} @0x{addr:08X}")
    t.halt(); raw=bytes(t.read_memory_block8(addr, PLANE)); t.resume()
a=np.frombuffer(raw,dtype="<u2").reshape(H,W)
r=((a>>11)&0x1F)*255//31; g=((a>>5)&0x3F)*255//63; b=(a&0x1F)*255//31
Image.fromarray(np.dstack([r,g,b]).astype(np.uint8),"RGB").save(r"D:\RTT\_re\shots\dbuf.png")
gg = np.asarray(Image.open(r"D:\RTT\_re\shots\dbuf.png").convert("L"),dtype=np.float32)
col=gg.mean(axis=0); c=col-col.mean(); ac=np.correlate(c,c,mode="full")[len(c)-1:]; ac/=(ac[0]+1e-6)
pk=int(np.argmax(ac[5:80])+5)
print(f"  亮度={gg.mean():.1f} 对比度={gg.std():.1f} 竖条周期={pk}px 相关={ac[pk]:.2f}")
print(f"  左条={gg[:,:70].mean():.1f} 右条={gg[:,-70:].mean():.1f}")
