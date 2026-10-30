from PIL import Image, ImageDraw
import random, os
base = r"D:\RTT\ml\_smoke"
for cls in ("yes","no"):
    d = os.path.join(base, cls); os.makedirs(d, exist_ok=True)
    for i in range(15):
        img = Image.new("RGB", (160,120), (40,40,40))
        dr = ImageDraw.Draw(img)
        if cls == "yes":
            dr.rectangle([60,40,100,80], fill=(200,200,190))
        else:
            dr.ellipse([60,40,100,80], fill=(70,70,70))
        ox, oy = random.randint(-4,4), random.randint(-4,4)
        img = img.transform(img.size, Image.AFFINE, (1,0,ox,0,1,oy))
        img.save(os.path.join(d, f"{i:02d}.jpg"))
print("synthetic images ready")
