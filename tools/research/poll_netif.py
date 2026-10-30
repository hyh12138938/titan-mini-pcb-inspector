import os, time, struct
os.environ['TMP'] = r'D:\RTT\_tmp'
os.environ['TEMP'] = r'D:\RTT\_tmp'

from pyocd.core.helpers import ConnectHelper

NETIF_DEFAULT = 0x220F4404

def ip(u):
    return '%d.%d.%d.%d' % (u & 0xff, (u >> 8) & 0xff, (u >> 16) & 0xff, (u >> 24) & 0xff)

last = None
for attempt in range(1, 9):
    s = ConnectHelper.session_with_chosen_probe(
        target_override='r7ka8p1kf',
        options={'auto_unlock': True, 'connect_mode': 'attach'})
    if s is None:
        print('attempt %d: no session' % attempt)
        time.sleep(3)
        continue
    with s:
        t = s.target
        try:
            p = int.from_bytes(bytes(t.read_memory_block8(NETIF_DEFAULT, 4)), 'little')
            if p:
                b = bytes(t.read_memory_block8(p, 16))
                nxt, ipa, msk, gw = struct.unpack('<IIII', b[0:16])
                txt = 'ip=%s mask=%s gw=%s' % (ip(ipa), ip(msk), ip(gw))
            else:
                txt = 'netif_default=NULL'
        except Exception as e:
            txt = 'read err %s' % e
    print('attempt %d: %s' % (attempt, txt), flush=True)
    last = txt
    if 'ip=0.0.0.0' not in txt and 'NULL' not in txt and 'err' not in txt:
        print('LEASE ACQUIRED')
        break
    time.sleep(4)
print('final:', last)
