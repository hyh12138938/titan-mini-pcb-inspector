import numpy as np, time
from pyocd.core.helpers import ConnectHelper
W,H = 800,480
BASE = 0x68096080
quad = np.zeros((H,W), dtype="<u2")
quad[:H//2, :W//2] = 0xF800   # 左上红
quad[:H//2, W//2:] = 0x07E0   # 右上绿
quad[H//2:, :W//2] = 0x001F   # 左下蓝
quad[H//2:, W//2:] = 0xFFFF   # 右下白
blob = quad.tobytes()
CH = 16*1024
with ConnectHelper.session_with_chosen_probe(target_override="r7ka8p1kf", frequency=1000000) as s:
    t = s.target
    t.halt()
    ok = 0
    for off in range(0, len(blob), CH):
        for attempt in range(3):
            try:
                t.write_memory_block8(BASE+off, blob[off:off+CH]); ok += 1; break
            except Exception:
                time.sleep(0.1)
    total = (len(blob)+CH-1)//CH
    print(f"  写入 {ok}/{total} 块")
    for name, addr, exp in (("左上", BASE, "00f8"), ("右上", BASE + (W//2)*2, "e007"),
                            ("左下", BASE + (H//2)*W*2, "1f00"), ("右下", BASE + (H//2)*W*2 + (W//2)*2, "ffff")):
        d = bytes(t.read_memory_block8(addr, 2)).hex()
        print(f"  {name}: {d} {'OK' if d==exp else 'MISMATCH(期望'+exp+')'}")
    t.resume()
