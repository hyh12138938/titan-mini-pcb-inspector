import re
D = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\libraries\Common\ports\mipicsi_camera"
CFG = D + r"\camera_layer_config.h"
CAM = D + r"\camera_layer.c"

c = open(CFG, "rb").read()
c = c.replace(b"(CONFIG_BRIGHTNESS_PLUS_3)", b"(CONFIG_BRIGHTNESS_ZERO)")
open(CFG, "wb").write(c)

c = open(CAM, "rb").read()
reps = [
    (b"{ 0x3a0f, 0x70 }", b"{ 0x3a0f, 0x40 }"),
    (b"{ 0x3a10, 0x60 }", b"{ 0x3a10, 0x30 }"),
    (b"{ 0x3a1b, 0x70 }", b"{ 0x3a1b, 0x40 }"),
    (b"{ 0x3a1e, 0x60 }", b"{ 0x3a1e, 0x30 }"),
    (b"{ 0x3a11, 0xf0 }", b"{ 0x3a11, 0x71 }"),
    (b"{ 0x3a1f, 0x40 }", b"{ 0x3a1f, 0x20 }"),
    (b"{ 0x3a18, 0xe0 }", b"{ 0x3a18, 0x00 }"),
]
for a, b in reps:
    c = c.replace(a, b)
open(CAM, "wb").write(c)
print("reverted to known-good")
