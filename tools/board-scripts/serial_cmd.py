import sys, time, serial

port = sys.argv[1]
cmds = sys.argv[2:]
s = serial.Serial(port, 115200, timeout=0.1)
s.reset_input_buffer()
time.sleep(0.2)
for c in cmds:
    print("\n### > %s" % c)
    s.write((c + "\r\n").encode())
    buf = b""
    t0 = time.time()
    while time.time() - t0 < 9:
        d = s.read(4096)
        if d:
            buf += d
            t0 = time.time()          # extend while data keeps coming
    txt = buf.decode("utf-8", "replace")
    print(txt.strip()[:1200])
s.close()
