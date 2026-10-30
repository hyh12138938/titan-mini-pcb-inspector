import re
for name in ["Titan_Mini_rgb_lcd", "Titan_Mini_cam_bright"]:
    p = rf"D:\RTT\sdk-bsp-ra8p1-titan-mini\project\{name}\rtthread.bin"
    try:
        b = open(p, "rb").read()
    except Exception as e:
        print(f"  {name}: 打不开 {e}")
        continue
    keys = [b"rgb lcd routine", b"camera", b"Hello RT-Thread", b"D2_BRIGHT", b"lcd"]
    hits = {k.decode(errors="ignore"): (k in b) for k in keys}
    print(f"  {name}: size={len(b)} -> {hits}")
