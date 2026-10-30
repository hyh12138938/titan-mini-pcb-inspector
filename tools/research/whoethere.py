import serial, time, sys
for port in ("COM4", "COM3"):
    try:
        s = serial.Serial(port, 115200, timeout=0.1)
    except Exception as e:
        print("%s: BUSY/OPEN FAIL -> %s" % (port, e))
        continue
    s.reset_input_buffer()
    s.write(b"\r\ndate\r\n")
    buf = b""
    t0 = time.time()
    while time.time() - t0 < 3:
        d = s.read(4096)
        if d:
            buf += d
    s.close()
    print("%s: %d bytes" % (port, len(buf)))
    print(repr(buf[:300]))
