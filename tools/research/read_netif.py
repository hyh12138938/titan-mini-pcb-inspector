import os, sys, time, struct
os.environ['TMP'] = r'D:\RTT\_tmp'
os.environ['TEMP'] = r'D:\RTT\_tmp'

from pyocd.core.helpers import ConnectHelper

ADDR_NETIF_DEFAULT = 0x220F4404
ADDR_NETIF_LIST = 0x220F4408

def ip(u):
    return '%d.%d.%d.%d' % (u & 0xff, (u >> 8) & 0xff, (u >> 16) & 0xff, (u >> 24) & 0xff)

session = ConnectHelper.session_with_chosen_probe(target_override='r7ka8p1kf',
                                                 options={'auto_unlock': True})
t = session.target
cores = []
try:
    cores = list(t.cores)
except Exception as e:
    print('cores err', e)
print('cores:', [(getattr(c, 'name', '?'), getattr(c, 'core_number', '?')) for c in cores])

reader = None
for cand in [t] + cores:
    try:
        cand.read_memory_block8(ADDR_NETIF_DEFAULT, 4)
        reader = cand
        print('reader =', type(cand).__name__, getattr(cand, 'name', ''))
        break
    except Exception as e:
        print('  try fail:', type(cand).__name__, getattr(cand, 'name', ''), e)

if reader is None:
    print('no reader')
else:
    p = int.from_bytes(bytes(reader.read_memory_block8(ADDR_NETIF_DEFAULT, 4)), 'little')
    lst = int.from_bytes(bytes(reader.read_memory_block8(ADDR_NETIF_LIST, 4)), 'little')
    print('netif_default = 0x%08X' % p)
    print('netif_list    = 0x%08X' % lst)
    if p:
        raw = bytes(reader.read_memory_block8(p, 64))
        print('netif[0:32] =', raw[:32].hex())
        nxt, ipa, msk, gw = struct.unpack('<IIII', raw[0:16])
        print('  ip_addr = %s   netmask = %s   gw = %s' % (ip(ipa), ip(msk), ip(gw)))

# leave running
for c in cores or [t]:
    try:
        c.resume()
        print('resumed', getattr(c, 'name', '?'))
    except Exception as e:
        print('resume fail', getattr(c, 'name', '?'), e)
time.sleep(0.3)
for c in cores or [t]:
    try:
        print('PC = 0x%08X' % c.read_core_register('pc'))
    except Exception as e:
        print('pc fail', getattr(c, 'name', '?'), e)
session.close()
print('closed')
