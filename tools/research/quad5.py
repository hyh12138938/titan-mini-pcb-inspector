import numpy as np, time
from pyocd.core.helpers import ConnectHelper
W,H = 800,480
BASE = 0x68096080
S = 80
patches = [(0,0,0xF800,"红"), (W-S,0,0x07E0,"绿"), (0,H-S,0x001F,"蓝"), (W-S,H-S,0xFFFF,"白")]
line = {c: (c.to_bytes(2,"little")*S) for _,_,c,_ in patches}

with ConnectHelper.session_with_chosen_probe(target_override="r7ka8p1kf", frequency=1000000) as s:
    t = s.target
    t.halt()
    for x0,y0,color,name in patches:
        for y in range(y0, y0+S):
            addr = BASE + (y*W + x0)*2
            for attempt in range(3):
                try:
                    t.write_memory_block8(addr, line[color]); break
                except Exception:
                    time.sleep(0.05)
        d = bytes(t.read_memory_block8(BASE + (y0*W + x0)*2, 2)).hex()
        print(f"  {name}色块 @({x0},{y0}) 回读={d}")
    t.resume()
    print("  四个色块写好")
