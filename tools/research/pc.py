from pyocd.core.helpers import ConnectHelper
with ConnectHelper.session_with_chosen_probe(target_override="r7ka8p1kf") as s:
    t=s.target; t.halt()
    print(f"PC=0x{t.read_core_register('pc'):08X}")
    t.resume()
