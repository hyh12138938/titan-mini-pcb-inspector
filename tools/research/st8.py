from pyocd.core.helpers import ConnectHelper
with ConnectHelper.session_with_chosen_probe(target_override='r7ka8p1kf') as s:
    t=s.target; t.halt()
    print(f'g_stage={t.read32(0x22020DDC)}')
    print(f'g_frames={t.read32(0x22020DD8)}')
    t.resume()
