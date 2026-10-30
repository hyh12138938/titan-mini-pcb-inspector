import serial, time, urllib.request, json, io
from PIL import Image, ImageStat

PORT="COM7"; URL="http://192.168.137.1:8001/frame"
def stats(): return json.loads(urllib.request.urlopen('http://127.0.0.1:8001/stats',timeout=5).read())
def luma():
    png = urllib.request.urlopen('http://127.0.0.1:8001/latest.png',timeout=5).read()
    im = Image.open(io.BytesIO(png)).convert("RGB"); st = ImageStat.Stat(im)
    return 0.299*st.mean[0]+0.587*st.mean[1]+0.114*st.mean[2], st.mean

s = serial.Serial(PORT, 115200, timeout=0.1)
def cmd(c, wait=0.8):
    s.reset_input_buffer(); s.write((c+"\r\n").encode()); time.sleep(wait)
    return s.read(16384).decode("utf-8","replace")

def push(tag=""):
    before = stats()["frames"]
    out = cmd("cam_push %s 2" % URL, 1.5)
    t0=time.time()
    while time.time()-t0 < 8:
        if stats()["frames"] > before: break
        time.sleep(0.2)
    time.sleep(0.6)
    l, mean = luma()
    print("%-28s luma=%6.1f  meanRGB=(%5.1f,%5.1f,%5.1f)" % (tag, l, mean[0], mean[1], mean[2]))
    return l

print(cmd("date 2026 10 22 22 30 00", 0.6).strip()[-40:])
cmd("cam_gain 1", 0.4); cmd("cam_bright 0", 0.4); cmd("cam_aec 1", 0.6)
print("--- auto exposure registers ---")
for r in ("3500","3501","3502","350a","350b","3503"):
    print(cmd("cam_regr "+r, 0.4).strip())
push("auto (baseline)")
print("--- AGC auto + manual exposure ---")
cmd("cam_reg 3503 01", 0.5)
for lines in (800, 1600, 3000):
    cmd("cam_exp %d" % lines, 0.6)
    push("exp=%d" % lines)
print("--- back to auto + brightness ---")
cmd("cam_exp 0", 0.6)
for b in (2, 4):
    cmd("cam_bright %d" % b, 0.5)
    push("auto bright=%d" % b)
s.close()
