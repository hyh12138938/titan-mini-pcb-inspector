import subprocess, time, os, sys
import serial

PORT = "COM4"
env = dict(os.environ)
env["TMP"] = r"D:\RTT\_tmp"
env["TEMP"] = r"D:\RTT\_tmp"

s = serial.Serial(PORT, 115200, timeout=0.1)
print("opened", PORT)
s.reset_input_buffer()

print("resetting board via pyocd ...")
try:
    rc = subprocess.run(["pyocd", "reset", "-t", "r7ka8p1kf"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        env=env, timeout=60).returncode
    print("pyocd reset rc =", rc)
except Exception as e:
    print("reset error:", e)

buf = b""
t0 = time.time()
while time.time() - t0 < 6:
    d = s.read(4096)
    if d:
        buf += d
print("boot bytes: %d" % len(buf))
if buf:
    print(repr(buf[:600]))
    print(buf.decode("utf-8", "replace")[:1200])

s.write(b"\r\n")
time.sleep(0.2)
s.write(b"ifconfig\r\n")
buf2 = b""
t0 = time.time()
while time.time() - t0 < 5:
    d = s.read(4096)
    if d:
        buf2 += d
print("cmd bytes: %d" % len(buf2))
if buf2:
    print(buf2.decode("utf-8", "replace")[:1500])
s.close()
print("closed")
