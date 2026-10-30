import numpy as np
from pyocd.core.helpers import ConnectHelper
W,H,PLANE = 800,480,800*480*2
BASE = 0x68096080          # 当前固件的 fb_background[0]（我们一直读的这块）
def paint(t, base):
    quad = np.zeros((H,W), dtype="<u2")
    quad[:H//2, :W//2] = 0xF800   # 左上 红
    quad[:H//2, W//2:] = 0x07E0   # 右上 绿
    quad[H//2:, :W//2] = 0x001F   # 左下 蓝
    quad[H//2:, W//2:] = 0xFFFF   # 右下 白
    t.write_memory_block8(base, quad.tobytes())
    d = bytes(t.read_memory_block8(base, 8))
    print(f"  已写入 4 象限到 0x{base:08X}，回读 {d.hex(' ')}")
with ConnectHelper.session_with_chosen_probe(target_override="r7ka8p1kf") as s:
    t=s.target
    t.halt()
    paint(t, BASE)
    t.resume()
