from PIL import Image
import os

src = r"D:\RTT\ai_images\img_20261022_124200_0.jpg"
im = Image.open(src).convert("RGB")
print("orig", im.size, os.path.getsize(src)//1024, "KB")

def make(target_kb, out):
    target = target_kb * 1024
    for scale in (1.0, 0.85, 0.7, 0.55, 0.45, 0.35, 0.25):
        w, h = im.size
        cur = im if scale == 1.0 else im.resize((max(1,int(w*scale)), max(1,int(h*scale))), Image.LANCZOS)
        for q in (88, 80, 72, 64, 55, 45):
            cur.save(out, "JPEG", quality=q, optimize=True)
            sz = os.path.getsize(out)
            if sz <= target:
                print("%-22s %4d KB  %s  q=%d scale=%.2f" % (os.path.basename(out), sz//1024, cur.size, q, scale))
                return
    print("cannot reach", target_kb, "KB")

make(64,  r"D:\RTT\ai_images\probe_64k.jpg")
make(128, r"D:\RTT\ai_images\probe_128k.jpg")
make(180, r"D:\RTT\ai_images\probe_180k.jpg")
