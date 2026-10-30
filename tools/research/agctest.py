import serial, time, urllib.request, json, io
from PIL import Image, ImageStat
PORT="COM7"; URL="http://192.168.137.1:8001/frame"
def stats(): return json.loads(urllib.request.urlopen('http://127.0.0.1:8001/stats',timeout=5).read())
def grab():
    png = urllib.request.urlopen('http://127.0.0.1:8001/latest.png',timeout=5).read()
    im = Image.open(io.BytesIO(png)).convert("RGB"); st = ImageStat.Stat(im)
    return (0.299*st.mean[0]+0.587*st.mean[1]+0.114*st.mean[2], st.mean, png)
s = serial.Serial(PORT, 115200, timeout=0.1)
def cmd(c, wait=0.8):
    s.reset_input_buffer(); s.write((c+"\r\n").encode()); time.sleep(wait)
    return s.read(16384).decode("utf-8","replace")
def push():
    before = stats()["frames"]
    cmd("cam_push %s 2" % URL, 1.2)
    t0=time.time()
    while time.time()-t0 < 8:
        if stats()["frames"] > before: break
        time.sleep(0.2)
    time.sleep(0.4)
    return grab()

cmd("date 2026 10 22 22 40 00", 0.6)
print(cmd("cam_agc 1 140", 0.5).strip())
for i in range(8):
    l, mean, png = push()
    print("frame %d  luma=%6.1f  meanRGB=(%5.1f,%5.1f,%5.1f)" % (i+1, l, mean[0], mean[1], mean[2]))
    open(r"D:\RTT\_tmp\agc_%d.png" % (i+1), "wb").write(png)
s.close()
