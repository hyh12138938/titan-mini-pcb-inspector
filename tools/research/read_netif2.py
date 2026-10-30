import os, sys, time, struct
os.environ['TMP'] = r'D:\RTT\_tmp'
os.environ['TEMP'] = r'D:\RTT\_tmp'

from pyocd.core.helpers import ConnectHelper

NETIF_DEFAULT = 0x220F4404
NETIF_LIST = 0x220F4408

def ip(u):
    return '%d.%d.%d.%d' % (u & 0xff, (u >> 8) & 0xff, (u >> 16) & 0xff, (u >> 24) & 0xff)

def attempt(mode):
    try:
        s = ConnectHelper.session_with_chosen_probe(
            target_override='r7ka8p1kf',
            options={'auto_unlock': True, 'connect_mode': mode})
    except Exception as e:
        print('  session fail', mode, e)
        return False
    if s is None:
        print('  session None', mode)
        return False
    with s:
        t = s.target
        cores = []
        try:
            cores = list(t.cores)
        except Exception:
            pass
        print('  mode=%s cores=%d' % (mode, len(cores)))
        try:
            raw = bytes(t.read_memory_block8(NETIF_DEFAULT, 4))
            p = int.from_bytes(raw, 'little')
            lst = int.from_bytes(bytes(t.read_memory_block8(NETIF_LIST, 4)), 'little')
            print('  netif_default=0x%08X netif_list=0x%08X' % (p, lst))
            if p:
                b = bytes(t.read_memory_block8(p, 32))
                nxt, ipa, msk, gw = struct.unpack('<IIII', b[0:16])
                print('  *** IP=%s netmask=%s gw=%s' % (ip(ipa), ip(msk), ip(gw)))
            return True
        except Exception as e:
            print('  read fail', e)
            return False

for mode in ('attach', 'halt'):
    print('try mode:', mode)
    if attempt(mode):
        break
    time.sleep(0.5)
print('done')
