import os, random, numpy as np
from PIL import Image
src = r"D:\RTT\ml\data\pcb_bin"; dst = r"D:\RTT\ml\calib"
os.makedirs(dst, exist_ok=True)
files = []
for c in ("good","defect"):
    files += [os.path.join(src,c,f) for f in os.listdir(os.path.join(src,c))]
random.seed(0); random.shuffle(files)
for i,f in enumerate(files[:120]):
    im = Image.open(f).convert("RGB").resize((96,96))
    a = np.asarray(im, dtype=np.float32)/255.0
    a = (a-0.5)/0.5
    np.save(os.path.join(dst, f"{i:03d}.npy"), a[None].astype(np.float32))   # 1,96,96,3
print("calib:", len(os.listdir(dst)), "shape", np.load(os.path.join(dst,"000.npy")).shape)
