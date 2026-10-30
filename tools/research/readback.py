from pyocd.core.helpers import ConnectHelper
with ConnectHelper.session_with_chosen_probe(target_override="r7ka8p1kf") as s:
    t=s.target; t.halt()
    for name, base, y in (("plane0", 0x68096080, 10), ("plane0", 0x68096080, 200),
                          ("plane1", 0x68151880, 200), ("plane1", 0x68151880, 10)):
        d = bytes(t.read_memory_block8(base + y*800*2, 6))
        print(f"  {name} 第{y}行: {d.hex(' ')}")
    t.resume()
