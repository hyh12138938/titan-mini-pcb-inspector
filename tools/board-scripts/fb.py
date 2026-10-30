from pyocd.core.helpers import ConnectHelper
with ConnectHelper.session_with_chosen_probe(target_override="r7ka8p1kf") as s:
    t = s.target
    t.halt()
    cur = t.read32(0x22000000)
    sing = t.read32(0x22020848)
    doub = t.read32(0x2202084C)
    print(f"lcd_current_working_buffer = 0x{cur:08X}")
    print(f"gp_single_buffer = 0x{sing:08X}   gp_double_buffer = 0x{0:08X}" .format(doub))
    for name, addr in (("fb_background", 0x681C2000), ("single", sing), ("double", doub)):
        if addr == 0:
            print(f"  {name}: 指针为 0")
            continue
        try:
            d = bytes(t.read_memory_block8(addr, 32))
            words = [int.from_bytes(d[i:i+2], "little") for i in range(0, 32, 2)]
            print(f"  {name} @0x{addr:08X}: " + " ".join(f"{w:04X}" for w in words))
        except Exception as e:
            print(f"  {name}: 读取失败 {e}")
    t.resume()
