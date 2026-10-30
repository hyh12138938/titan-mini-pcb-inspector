P = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\libraries\Common\ports\mipicsi_camera\camera_layer.c"
b = open(P,"rb").read()
old = b"{ 0x3a00, 0x3c }"
new = b"{ 0x3a00, 0x21 }"
print("found:", old in b)
open(P,"wb").write(b.replace(old,new))
