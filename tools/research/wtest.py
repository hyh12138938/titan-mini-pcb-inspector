from pyocd.core.helpers import ConnectHelper
CANDIDATES = [0x68096080, 0x68151880, 0x681C2000, 0x68000000, 0x68096000]
with ConnectHelper.session_with_chosen_probe(target_override="r7ka8p1kf") as s:
    t=s.target
    t.halt()
    for a in CANDIDATES:
        try:
            t.write_memory_block8(a, b"\xAA\x55" * 8)
            got = bytes(t.read_memory_block8(a, 8))
            print(f"  0x{a:08X}: 写 AA55 -> 回读 {got.hex(' ')}  {'OK' if got[:4]==b'\xaa\x55\xaa\x55' else 'FAIL'}")
        except Exception as e:
            print(f"  0x{a:08X}: 异常 {e}")
    t.resume()
