import serial, time
s = serial.Serial("COM7", 115200, timeout=0.2)
def cmd(c, wait=1.5):
    s.reset_input_buffer(); s.write((c+"\r\n").encode()); time.sleep(wait)
    return s.read(16384).decode("utf-8","replace").strip()
print("--- cam_stream stop ---"); print(cmd("cam_stream stop", 1.2)[-300:])
print("--- cam_stats ---");      print(cmd("cam_stats", 3.0)[-400:])
print("--- cam_push ---");       print(cmd("cam_push http://192.168.137.1:8001/frame 4", 3.0)[-400:])
print("--- cam_stats again ---");print(cmd("cam_stats", 3.0)[-400:])
s.close()
