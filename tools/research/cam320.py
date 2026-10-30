import urllib.request, json, time
def stats(): return json.loads(urllib.request.urlopen('http://127.0.0.1:8001/stats',timeout=5).read())
a=stats(); time.sleep(3); b=stats()
print("320x240 @8fps -> measured fps =", round((b['frames']-a['frames'])/3.0,1), "size", b['w'], b['h'], "bytes", b['last_bytes'])
p=urllib.request.urlopen('http://127.0.0.1:8001/latest.png',timeout=5).read()
open(r'D:\RTT\_tmp\cam_320.png','wb').write(p); print("png", len(p))
