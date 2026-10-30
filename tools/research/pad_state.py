from pyocd.core.helpers import ConnectHelper
SYM = {"dbg_err":0x22020E08, "dbg_result":0x22020E0C, "dbg_good_q":0x22020E18, "dbg_defect_q":0x22020E1C}
with ConnectHelper.session_with_chosen_probe(target_override="r7ka8p1kf") as s:
    t=s.target
    t.halt()
    print(f"PC=0x{t.read_core_register('pc'):08X}")
    for k,a in SYM.items():
        print(f"  {k} = {t.read32(a)}")
    t.resume()
