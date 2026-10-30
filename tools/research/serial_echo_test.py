import time, sys, serial

PORT = "COM4"
BAUD = 115200
TEST = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

s = serial.Serial(PORT, BAUD, timeout=0.1)
s.reset_input_buffer()
time.sleep(0.2)
s.write(b"\r\n")
time.sleep(0.5)
s.reset_input_buffer()

print("=== 1) finsh 字符回显（板子收到的每个字符都会回送）===")
print("发送: %s" % TEST)
s.write(TEST.encode())
buf = b""
t0 = time.time()
while time.time() - t0 < 2.5:
    d = s.read(4096)
    if d:
        buf += d
        t0 = time.time()
echo = buf.decode("utf-8", "replace")
print("收到: %r" % echo)

if TEST in echo:
    print("结果: PASS  —— 36 个字符原样回显，TX/RX 双向都通")
else:
    print("结果: FAIL —— 回显不完整或不匹配")

# 收尾：把这一行取消掉，回到提示符
s.write(b"\x15")          # Ctrl-U 清除当前行
time.sleep(0.3)
s.write(b"\r\n")
time.sleep(0.5)
tail = b""
t0 = time.time()
while time.time() - t0 < 1.5:
    d = s.read(4096)
    if d:
        tail += d
print("\n=== 2) 回到提示符 ===")
print(tail.decode("utf-8", "replace").strip()[-200:])
s.close()
