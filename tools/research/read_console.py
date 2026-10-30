import os, time
os.environ['TMP'] = r'D:\RTT\_tmp'
os.environ['TEMP'] = r'D:\RTT\_tmp'
from pyocd.core.helpers import ConnectHelper

CONSOLE_DEV = 0x220FAB14
UART1_CTRL  = 0x220FA6CC

s = ConnectHelper.session_with_chosen_probe(target_override='r7ka8p1kf',
                                            options={'auto_unlock': True, 'connect_mode': 'attach'})
with s:
    t = s.target
    p = int.from_bytes(bytes(t.read_memory_block8(CONSOLE_DEV, 4)), 'little')
    print('_console_device = 0x%08X' % p)
    if p:
        raw = bytes(t.read_memory_block8(p, 16))
        print('device head bytes:', raw.hex())
        name = raw.split(b'\x00')[0]
        print('device name =', name)
    ctrl = bytes(t.read_memory_block8(UART1_CTRL, 32))
    print('g_uart1_ctrl[0:32] =', ctrl.hex())
print('done')
