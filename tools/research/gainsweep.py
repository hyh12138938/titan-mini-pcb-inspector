import serial, time, urllib.request, json
from PIL import Image, ImageStat
import io

PORT="COM7"; URL="http://192.168.137.1:8001/frame"
def stats():
    return json.loads(urllib.request.urlopen('http://127.0.0.1:8001/stats',timeout=5).read())
def fetch_png():
    return urllib.request.urlopen('http://127.0.0.1:8001/latest.png',timeout=5).read()
def luma(png):
    im = Image.open(io.BytesIO(png)).convert("RGB")
    st = ImageStat.Stat(im)
    return 0.299*st.mean[0]+0.587*st.mean[1]+0.114*st.mean[2]

s = serial.Serial(PORT, 115200, timeout=0.1)
def cmd(c, wait=1.2):
    s.reset_input_buffer()
    s.write((c+"\r\n").encode())
    time.sleep(wait)
    return s.read(8192).decode("utf-8","replace")

print(cmd("date 2026 10 22 22 20 00"))
print(cmd("cam_gain 1", 0.5))
print(cmd("cam_push %s 2" % URL, 1.0))
time.sleep(2.5)
base = stats()["frames"]
print("baseline frames", base, "phone luma = 155.5")
for g in (1,2,3,4):
    print(cmd("cam_gain %d" % g, 0.4).strip()[-40:])
    before = stats()["frames"]
    print(cmd("cam_push %s 2" % URL, 1.0).strip()[-60:])
    t0=time.time()
    while time.time()-t0 < 8:
        if stats()["frames"] > before: break
        time.sleep(0.3)
    png = fetch_png()
    print("gain=%d -> luma=%.1f (png %d B)" % (g, luma(png), len(png)))
    open(r"D:\RTT\_tmp\gain_%d.png" % g, "wb").write(png)
s.close()
