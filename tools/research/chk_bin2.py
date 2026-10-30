p = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\project\Titan_Mini_display_camera_mipi_csi\rtthread.bin"
b = open(p, "rb").read()
for k in [b"camera", b"rgb lcd routine", b"Hello RT-Thread", b"mipi"]:
    print(f"  {k.decode():16s} {'YES' if k in b else 'no'}")
print(f"  size = {len(b)} B")
