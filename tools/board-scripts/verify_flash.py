import sys, os, time
os.environ['TMP'] = r'D:\RTT\_tmp'
os.environ['TEMP'] = r'D:\RTT\_tmp'

from pyocd.core.helpers import ConnectHelper

HEX = r'D:\RTT\sdk-bsp-ra8p1-titan-mini\project\Titan_Mini_driver_eth\rtthread.hex'

def hex_parse(path, base, n):
    mem = {}
    upper = 0
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line.startswith(':'):
                continue
            b = bytes.fromhex(line[1:])
            ln, addr, rt = b[0], (b[1] << 8) | b[2], b[3]
            if rt == 0x04:                      # extended linear address
                upper = ((b[4] << 8) | b[5]) << 16
            elif rt == 0x00:
                for i in range(ln):
                    mem[upper + addr + i] = b[4 + i]
    return bytes(mem.get(base + i, 0xff) for i in range(n))

exp = hex_parse(HEX, 0x02000000, 64)
print('expected @0x02000000:', exp.hex())

session = ConnectHelper.session_with_chosen_probe(target_override='r7ka8p1kf',
                                                options={'auto_unlock': True})
with session:
    t = session.target
    data = bytes(t.read_memory_block8(0x02000000, 64))
    print('actual   @0x02000000:', data.hex())
    print('IMAGE MATCH (64B):', data == exp)

    print('state =', t.get_state())
    pcs = []
    for _ in range(3):
        try:
            pcs.append(t.read_core_register('pc'))
        except Exception as e:
            pcs.append('err:%s' % e)
        time.sleep(0.15)
    print('PC samples:', ['0x%08X' % p if isinstance(p, int) else p for p in pcs])

    for name, addr in (('CFSR', 0xE000ED28), ('HFSR', 0xE000ED2C), ('VTOR', 0xE000ED08)):
        try:
            v = t.read32(addr)
            print('%s = 0x%08X' % (name, v))
        except Exception as e:
            print(name, 'err', e)
