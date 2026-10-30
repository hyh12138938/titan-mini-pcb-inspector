from PIL import Image, ImageDraw
import io, os

W, H = 320, 240
img = Image.new("RGB", (W, H), (245, 245, 245))
d = ImageDraw.Draw(img)
d.rectangle([10, 10, 310, 230], outline=(0, 0, 0), width=3)
d.ellipse([40, 60, 140, 160], fill=(220, 40, 40))          # red circle
d.rectangle([170, 70, 280, 150], fill=(40, 80, 220))        # blue rectangle
d.text((100, 190), "TITAN MINI 320x240", fill=(0, 0, 0))
d.text((100, 205), "red circle / blue box", fill=(0, 0, 0))

buf = io.BytesIO()
img.save(buf, format="JPEG", quality=82)
data = buf.getvalue()
print("jpeg bytes:", len(data))
open(r"D:\RTT\_tmp\vlm_sample.jpg", "wb").write(data)

out = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\project\Titan_Mini_driver_eth\src\vlm_sample_img.c"
with open(out, "w", encoding="ascii", newline="\n") as f:
    f.write("/* auto-generated test image: 320x240 JPEG, red circle + blue rectangle + text */\n")
    f.write("#include <rtthread.h>\n\n")
    f.write("const unsigned int g_vlm_sample_len = %d;\n\n" % len(data))
    f.write("const unsigned char g_vlm_sample_jpg[] =\n{\n")
    per = 16
    for i in range(0, len(data), per):
        chunk = data[i:i+per]
        f.write("    " + ",".join("0x%02X" % b for b in chunk) + ",\n")
    f.write("};\n")
print("wrote", out, os.path.getsize(out), "bytes")
