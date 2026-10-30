from pyocd.core.helpers import ConnectHelper
with ConnectHelper.session_with_chosen_probe(target_override='r7ka8p1kf') as s:
    t=s.target; t.halt()
    print(f'PC=0x{t.read_core_register("pc"):08X}')
    print(f'g_stage={t.read32(0x22020D60)}')
    print(f'g_frames={t.read32(0x22020D5C)}')
    print(f'cam_boot_state={t.read32(0x22020D58)}')
    t.resume()
