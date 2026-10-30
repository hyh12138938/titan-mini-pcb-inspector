P = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\libraries\Common\ports\mipicsi_camera\camera_layer.c"
b = open(P, "rb").read()
reps = [(b"{ 0x3a0f, 0x40 }", b"{ 0x3a0f, 0x60 }"),
        (b"{ 0x3a10, 0x30 }", b"{ 0x3a10, 0x50 }"),
        (b"{ 0x3a1b, 0x40 }", b"{ 0x3a1b, 0x60 }"),
        (b"{ 0x3a1e, 0x30 }", b"{ 0x3a1e, 0x50 }")]
for a,c in reps:
    print(f"  {a.decode()} -> {c.decode()}: {a in b}")
    b = b.replace(a,c)
open(P,"wb").write(b)
