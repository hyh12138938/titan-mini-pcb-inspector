P = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\libraries\Common\ports\mipicsi_camera\camera_layer.c"
b = open(P,"rb").read()
print("0x21 present:", b"{ 0x3a00, 0x21 }" in b)
open(P,"wb").write(b.replace(b"{ 0x3a00, 0x21 }", b"{ 0x3a00, 0x3c }"))
