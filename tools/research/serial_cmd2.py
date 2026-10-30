import sys, time, serial, io

port = sys.argv[1]
cmds = sys.argv[2:]
out = []
s = serial.Serial(port, 115200, timeout=0.1)
s.reset_input_buffer()
time.sleep(0.2)
for c in cmds:
    out.append("\n### > %s" % c)
    s.write((c + "\r\n").encode())
    buf = b""
    t0 = time.time()
    while time.time() - t0 < 9:
        d = s.read(4096)
        if d:
            buf += d
            t0 = time.time()
    out.append(buf.decode("utf-8", "replace").strip()[:2000])
s.close()
txt = "\n".join(out)
open(r"D:\RTT\_tmp\serial_out.txt", "w", encoding="utf-8").write(txt)
sys.stdout.write(txt.encode("ascii", "replace").decode("ascii"))
