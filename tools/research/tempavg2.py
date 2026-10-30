import serial, time, urllib.request, json, io
import numpy as np
from PIL import Image, ImageStat
PORT="COM7"; URL="http://192.168.137.1:8001/frame"
def stats(): return json.loads(urllib.request.urlopen('http://127.0.0.1:8001/stats',timeout=5).read())
s = serial.Serial(PORT, 115200, timeout=0.1)
def cmd(c, wait=0.9):
    s.reset_input_buffer(); s.write((c+"\r\n").encode()); time.sleep(wait)
    return s.read(16384).decode("utf-8","replace")
def push_grab(div=4):
    before = stats()["frames"]
    cmd("cam_push %s %d" % (URL, div), 1.3)
    t0=time.time()
    while time.time()-t0 < 10:
        if stats()["frames"] > before: break
        time.sleep(0.2)
    time.sleep(0.4)
    return Image.open(io.BytesIO(urllib.request.urlopen('http://127.0.0.1:8001/latest.png',timeout=5).read())).convert("RGB")

cmd("cam_csat 60", 0.4); cmd("cam_agc 1 150", 0.4)
push_grab()
frames = [push_grab() for _ in range(4)]
w,h = frames[0].size
box = (w//2-30, h//2-30, w//2+30, h//2+30)
def sdc(im):
    sd = ImageStat.Stat(im.crop(box)).stddev
    return float(sd[0]), float(sd[1]), float(sd[2])
print("single  (%.1f,%.1f,%.1f)" % sdc(frames[0]))
arrs = [np.asarray(f, dtype=np.float32) for f in frames]
for n in (2,4):
    a = np.clip(sum(arrs[:n])/float(n), 0, 255).astype(np.uint8)
    print("avg%d    (%.1f,%.1f,%.1f)" % ((n,)+sdc(Image.fromarray(a))))
    Image.fromarray(a).save(r"D:\RTT\_tmp\temporal_avg%d.png" % n)
frames[0].save(r"D:\RTT\_tmp\temporal_single.png")
s.close()
