import serial, time, urllib.request, json, io
from PIL import Image, ImageStat
PORT="COM7"; URL="http://192.168.137.1:8001/frame"
def stats(): return json.loads(urllib.request.urlopen('http://127.0.0.1:8001/stats',timeout=5).read())
s = serial.Serial(PORT, 115200, timeout=0.1)
def cmd(c, wait=0.9):
    s.reset_input_buffer(); s.write((c+"\r\n").encode()); time.sleep(wait)
    return s.read(16384).decode("utf-8","replace")
def push(tag, div=4):
    before = stats()["frames"]
    cmd("cam_push %s %d" % (URL, div), 1.4)
    t0=time.time()
    while time.time()-t0 < 10:
        if stats()["frames"] > before: break
        time.sleep(0.2)
    time.sleep(0.5)
    png = urllib.request.urlopen('http://127.0.0.1:8001/latest.png',timeout=5).read()
    im = Image.open(io.BytesIO(png)).convert("RGB"); st = ImageStat.Stat(im)
    l = 0.299*st.mean[0]+0.587*st.mean[1]+0.114*st.mean[2]
    w,h = im.size
    sd = ImageStat.Stat(im.crop((w//2-30,h//2-30,w//2+30,h//2+30))).stddev
    print("%-12s luma=%5.1f stddev=(%.1f,%.1f,%.1f)" % (tag, l, sd[0], sd[1], sd[2]))
    open(r"D:\RTT\_tmp\cs_%s.png" % tag, "wb").write(png)

cmd("date 2026 10 22 23 00 00", 0.6)
cmd("cam_fmt 888", 0.4); cmd("cam_agc 1 150", 0.5); cmd("cam_cnr 1", 0.4)
for v in (100, 70, 45, 20):
    cmd("cam_csat %d" % v, 0.4)
    push("sat%d" % v); push("sat%d_b" % v)
s.close()
