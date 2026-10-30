import urllib.request, struct
W,H = 320,240
buf = bytearray()
for y in range(H):
    for x in range(W):
        r = int(31*x/W); g = int(63*y/H); b = int(31*((x//20 + y//20) % 2))
        v = (r<<11)|(g<<5)|b
        buf += bytes([v & 0xFF, (v>>8)&0xFF])
req = urllib.request.Request("http://127.0.0.1:8001/frame", data=bytes(buf), method="POST",
      headers={"X-Width":str(W),"X-Height":str(H),"X-Format":"rgb565","X-Byte-Order":"le",
               "Content-Type":"application/octet-stream"})
print("POST ->", urllib.request.urlopen(req, timeout=5).status)
print("stats  ->", urllib.request.urlopen("http://127.0.0.1:8001/stats", timeout=5).read().decode())
png = urllib.request.urlopen("http://127.0.0.1:8001/latest.png", timeout=5).read()
print("png bytes =", len(png), png[:8])
open(r"D:\RTT\_tmp\camweb_test.png","wb").write(png)
