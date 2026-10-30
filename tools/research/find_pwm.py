from pyocd.core.helpers import ConnectHelper
with ConnectHelper.session_with_chosen_probe(target_override="r7ka8p1kf") as s:
    t=s.target; t.halt()
    for start,size,label in ((0x22020000,0x60000,"SRAM"),(0x22080000,0x80000,"SRAM2")):
        try:
            d=bytes(t.read_memory_block8(start,size))
        except Exception as e:
            print(label,"read fail",e); continue
        for name in (b"pwm7\x00", b"lcd\x00", b"pwm12\x00"):
            idx=d.find(name); hits=[]
            while idx!=-1 and len(hits)<3:
                hits.append(start+idx); idx=d.find(name, idx+1)
            if hits: print(f"  {label} {name.decode(errors='replace'):8s} -> " + ", ".join(f"0x{a:08X}" for a in hits))
            else: print(f"  {label} {name.decode(errors='replace'):8s} -> 未找到")
    t.resume()
