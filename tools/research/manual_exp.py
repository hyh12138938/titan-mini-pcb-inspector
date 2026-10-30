P = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\libraries\Common\ports\mipicsi_camera\camera_layer.c"
b = open(P,"rb").read()
anchor = b"    { 0x3a00, 0x3c },"
# 用更宽松的定位：直接找 "{ 0x3a00, 0x3c }" 所在行首
idx = b.find(b"{ 0x3a00, 0x3c }")
assert idx != -1
line_start = b.rfind(b"\n", 0, idx) + 1
insert = (b"{ 0x3503, 0x03 }, // manual exposure & gain\r\n"
          b"    { 0x3500, 0x00 }, { 0x3501, 0x08 }, { 0x3502, 0x00 }, // exposure = 0x0800\r\n"
          b"    { 0x3508, 0x02 }, { 0x3509, 0x00 }, // analog gain = 2x\r\n"
          b"    ")
b = b[:line_start] + insert + b[line_start:]
open(P,"wb").write(b)
print("inserted manual exposure before 0x3a00")
