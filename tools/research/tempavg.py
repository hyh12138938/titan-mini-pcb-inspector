import serial, time, urllib.request, json, io
from PIL import Image, ImageStat, ImageChops
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
push_grab()   # warm up AGC
frames = [push_grab() for _ in range(4)]
w,h = frames[0].size
def sd(im):
    st = ImageStat.Stat(im); return st.stddev
def sdc(im):
    return ImageStat.Stat(im.crop((w//2-30,h//2-30,w//2+30,h//2+30))).stddev
print("single   center_stddev=(%.1f,%.1f,%.1f)" % sdc(frames[0]))
# 平均
import numpy as np
arrs = [np.asarray(f, dtype=np.float32) for f in frames]
avg2 = np.clip((arrs[0]+arrs[1])/2, 0, 255).astype(np.uint8)
avg4 = np.clip(sum(arrs)/4.0, 0, 255).astype(np.uint8)
for name, a in (("avg2", avg2), ("avg4", avg4)):
    im = Image.fromarray(a)
    print("%s   center_stddev=(%.1f,%.1f,%.1f)" % ((name,)+tuple(sdc(im))))
Image.fromarray(avg4).save(r"D:\RTT\_tmp\temporal_avg4.png")
frames[0].save(r"D:\RTT\_tmp\temporal_single.png")
s.close()
