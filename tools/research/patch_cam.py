import re
D = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\libraries\Common\ports\mipicsi_camera"
CFG = D + r"\camera_layer_config.h"
CAM = D + r"\camera_layer.c"

# 1) 亮度 +3
c = open(CFG, "rb").read()
old = b"#define CAMERA_CONFIG_BRIGHTNESS     (CONFIG_BRIGHTNESS_ZERO)"
new = b"#define CAMERA_CONFIG_BRIGHTNESS     (CONFIG_BRIGHTNESS_PLUS_3)"
print("brightness patched:", old in c)
c = c.replace(old, new)
open(CFG, "wb").write(c)

# 2) AEC 目标/增益上限
c = open(CAM, "rb").read()
reps = [
    (b"{ 0x3a0f, 0x40 }", b"{ 0x3a0f, 0x70 }"),
    (b"{ 0x3a10, 0x30 }", b"{ 0x3a10, 0x60 }"),
    (b"{ 0x3a1b, 0x40 }", b"{ 0x3a1b, 0x70 }"),
    (b"{ 0x3a1e, 0x30 }", b"{ 0x3a1e, 0x60 }"),
    (b"{ 0x3a11, 0x71 }", b"{ 0x3a11, 0xf0 }"),
    (b"{ 0x3a1f, 0x20 }", b"{ 0x3a1f, 0x40 }"),
    (b"{ 0x3a18, 0x00 }", b"{ 0x3a18, 0xe0 }"),
]
for a, b in reps:
    ok = a in c
    c = c.replace(a, b)
    print(f"  {a.decode()} -> {b.decode()}  {'OK' if ok else 'MISS'}")
open(CAM, "wb").write(c)
print("done")
