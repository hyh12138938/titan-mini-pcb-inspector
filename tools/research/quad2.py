import numpy as np, time
from pyocd.core.helpers import ConnectHelper
W,H,PLANE = 800,480,800*480*2
BASE = 0x68096080
quad = np.zeros((H,W), dtype="<u2")
quad[:H//2, :W//2] = 0xF800
quad[:H//2, W//2:] = 0x07E0
quad[H//2:, :W//2] = 0x001F
quad[H//2:, W//2:] = 0xFFFF
blob = quad.tobytes()

def paint_chunked(t, base, data, chunk=32*1024):
    for off in range(0, len(data), chunk):
        piece = data[off:off+chunk]
        for attempt in range(3):
            try:
                t.write_memory_block8(base+off, piece)
                break
            except Exception as e:
                if attempt == 2: raise
                time.sleep(0.2)
    return True

with ConnectHelper.session_with_chosen_probe(target_override="r7ka8p1kf") as s:
    t = s.target
    t.halt()
    paint_chunked(t, BASE, blob)
    d = bytes(t.read_memory_block8(BASE, 8))
    d2 = bytes(t.read_memory_block8(BASE + (H//2)*W*2 + (W//2)*2, 8))
    print(f"  写入完成 0x{BASE:08X}")
    print(f"  左上回读 {d.hex(' ')}  (红=00 f8)")
    print(f"  右下回读 {d2.hex(' ')} (白=ff ff)")
    t.resume()
