import subprocess, sys, time, os

PORT = sys.argv[1] if len(sys.argv) > 1 else 'COM3'
BAUD = 115200

try:
    import serial
except Exception as e:
    print('no pyserial', e)
    sys.exit(1)

try:
    s = serial.Serial(PORT, BAUD, timeout=0.2)
except Exception as e:
    print('OPEN FAIL:', e)
    sys.exit(2)

print('opened', PORT, 'at', BAUD)
s.reset_input_buffer()

env = dict(os.environ)
env['TMP'] = r'D:\RTT\_tmp'
env['TEMP'] = r'D:\RTT\_tmp'

print('--- resetting board ---')
try:
    p = subprocess.run(['pyocd', 'reset', '-t', 'r7ka8p1kf'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       env=env, timeout=40)
    print('pyocd reset rc =', p.returncode)
except Exception as e:
    print('reset err', e)

buf = b''
t0 = time.time()
while time.time() - t0 < 8:
    d = s.read(4096)
    if d:
        buf += d

print('--- boot output (%d bytes) ---' % len(buf))
print(buf.decode('utf-8', 'replace'))

# ask for ifconfig
s.write(b'\r\nifconfig\r\n')
buf2 = b''
t0 = time.time()
while time.time() - t0 < 6:
    d = s.read(4096)
    if d:
        buf2 += d
print('--- ifconfig output (%d bytes) ---' % len(buf2))
print(buf2.decode('utf-8', 'replace'))

s.close()
