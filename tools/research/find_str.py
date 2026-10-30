from pyocd.core.helpers import ConnectHelper
PAT = b"NO CAMERA"
with ConnectHelper.session_with_chosen_probe(target_override="r7ka8p1kf") as s:
    t=s.target; t.halt()
    d=bytes(t.read_memory_block8(0x02000000, 0x100000))
    i=d.find(PAT)
    print(f"  目标 MRAM 搜索结果: {'找到 @0x%08X' % (0x02000000+i) if i>=0 else '未找到'}")
    print(f"    (ELF 里的位置: 0x{0x02000000+$found:08X})" if $found>=0 else "")
    t.resume()
