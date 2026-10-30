import time, sys
import serial
from serial.tools import list_ports

ports = sorted(list_ports.comports(), key=lambda p: p.device)
print("=== ports ===")
for p in ports:
    print("  %-6s %s | %s" % (p.device, p.description, p.hwid))

for p in ports:
    dev = p.device
    print("\n=== probing %s ===" % dev)
    try:
        s = serial.Serial(dev, 115200, timeout=0.2)
    except Exception as e:
        print("  open failed:", e)
        continue
    try:
        s.reset_input_buffer()
        s.write(b"\r\n")
        time.sleep(0.3)
        s.write(b"ifconfig\r\n")
        buf = b""
        t0 = time.time()
        while time.time() - t0 < 4:
            d = s.read(4096)
            if d:
                buf += d
        print("  bytes: %d" % len(buf))
        if buf:
            txt = buf.decode("utf-8", "replace")
            print("  ---- begin ----")
            print(txt[:1500])
            print("  ---- end ----")
    finally:
        s.close()
print("\ndone")
