import os, sys, time
os.environ['TMP'] = r'D:\RTT\_tmp'
os.environ['TEMP'] = r'D:\RTT\_tmp'

import serial
from pyocd.core.helpers import ConnectHelper

PORT = 'COM3'
s = serial.Serial(PORT, 115200, timeout=0.1)
print('serial open', PORT)
s.reset_input_buffer()

session = ConnectHelper.session_with_chosen_probe(target_override='r7ka8p1kf',
                                                 options={'auto_unlock': True})
t = session.target
print('connect ok, state =', t.get_state())
t.reset()
time.sleep(0.3)
try:
    print('PC after reset = 0x%08X' % t.read_core_register('pc'))
except Exception as e:
    print('pc err', e)
try:
    t.resume()
    print('resumed, state =', t.get_state())
except Exception as e:
    print('resume err', e)
time.sleep(0.1)
print('state before close =', t.get_state())
session.close()
try:
    print('state after close =', t.get_state())
except Exception as e:
    print('post-close state err', e)

buf = b''
t0 = time.time()
while time.time() - t0 < 5:
    d = s.read(4096)
    if d:
        buf += d
print('--- boot bytes: %d ---' % len(buf))
print(buf.decode('utf-8', 'replace'))

s.write(b'\r\nifconfig\r\n')
buf2 = b''
t0 = time.time()
while time.time() - t0 < 5:
    d = s.read(4096)
    if d:
        buf2 += d
print('--- ifconfig bytes: %d ---' % len(buf2))
print(buf2.decode('utf-8', 'replace'))
s.close()
