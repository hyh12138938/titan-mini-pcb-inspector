import urllib.request, json, time, hashlib
def stats(): return json.loads(urllib.request.urlopen('http://127.0.0.1:8001/stats',timeout=5).read())
a = stats(); p1 = urllib.request.urlopen('http://127.0.0.1:8001/latest.png',timeout=5).read()
time.sleep(1.2)
b = stats(); p2 = urllib.request.urlopen('http://127.0.0.1:8001/latest.png',timeout=5).read()
print("frames", a['frames'], "->", b['frames'], " fps=", round(b['fps'],1))
print("frame changed:", hashlib.md5(p1).hexdigest() != hashlib.md5(p2).hexdigest(), len(p1), len(p2))
open(r'D:\RTT\_tmp\cam_live1.png','wb').write(p1)
open(r'D:\RTT\_tmp\cam_live2.png','wb').write(p2)
