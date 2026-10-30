import numpy as np, time
from pyocd.core.helpers import ConnectHelper
W,H = 800,480
BASE = 0x68096080
quad = np.zeros((H,W), dtype="<u2")
quad[:H//2, :W//2] = 0xF800
quad[:H//2, W//2:] = 0x07E0
quad[H//2:, :W//2] = 0x001F
quad[H//2:, W//2:] = 0xFFFF
blob = quad.tobytes()
CH = 16*1024
with ConnectHelper.session_with_chosen_probe(target_override="r7ka8p1kf") as s:
    t = s.target
    t.halt()
    ok = 0
    for off in range(0, len(blob), CH):
        piece = blob[off:off+CH]
        for attempt in range(4):
            try:
                t.write_memory_block8(BASE+off, piece); ok += 1; break
            except Exception as e:
                time.sleep(0.15)
        else:
            print(f"  写入失败于 offset 0x{off:X}")
    print(f"  完成 {ok} 块 / 共 {(len(blob)+CH-1)//CH} 块")
    a = bytes(t.read_memory_block8(BASE, 8))
    b = bytes(t.read_memory_block8(BASE + (H//2)*W*2 + (W//2)*2, 8))
    print(f"  左上(应 00 f8 红) = {a.hex(' ')}")
    print(f"  右下(应 ff ff 白) = {b.hex(' ')}")
    t.resume()
