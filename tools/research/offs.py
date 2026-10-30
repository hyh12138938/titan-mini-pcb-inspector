from pyocd.core.helpers import ConnectHelper
with ConnectHelper.session_with_chosen_probe(target_override="r7ka8p1kf") as s:
    t=s.target; t.halt()
    base=0x220208B8
    for off in (0x40,0x44,0x48,0x4c,0x50,0x5c,0x60,0x64):
        v=int.from_bytes(bytes(t.read_memory_block8(base+off,4)),"little")
        print(f"  +0x{off:02X} = 0x{v:08X}")
    t.resume()
