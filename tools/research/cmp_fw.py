from pyocd.core.helpers import ConnectHelper
BIN = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\project\Titan_Mini_pad_inspect\_cmp.bin"
img = open(BIN, "rb").read()
BASE = 0x02000000
with ConnectHelper.session_with_chosen_probe(target_override="r7ka8p1kf") as s:
    t = s.target
    t.halt()
    for off in (0x0, 0x1000, 0x20000):
        got = bytes(t.read_memory_block8(BASE + off, 32))
        exp = img[off:off+32]
        same = got == exp
        print(f"  +0x{off:06X}: {'一致' if same else '不一致'}")
        if not same:
            print(f"    目标: {got.hex(' ')}")
            print(f"    ELF : {exp.hex(' ')}")
    t.resume()
