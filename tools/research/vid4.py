import glob, numpy as np
from PIL import Image
# 面板大致区域（沿用之前目测值）
X0,X1,Y0,Y1 = 370,1070,150,580
for f in sorted(glob.glob(r"D:\RTT\_re\video4\f_*.png")):
    im = np.asarray(Image.open(f).convert("RGB")).astype(np.float32)
    p = im[Y0:Y1, X0:X1]
    h,w,_ = p.shape
    def blk(y0,y1,x0,x1): return p[int(h*y0):int(h*y1), int(w*x0):int(w*x1)].reshape(-1,3).mean(axis=0)
    tl, tr = blk(0.05,0.25,0.05,0.25), blk(0.05,0.25,0.75,0.95)
    bl, br = blk(0.75,0.95,0.05,0.25), blk(0.75,0.95,0.75,0.95)
    def tag(c):
        r,g,b = c
        if r>150 and g<110 and b<110: return "红"
        if b>150 and r<110: return "蓝"
        if abs(r-g)<35 and abs(g-b)<35 and 90<r<200: return "灰"
        return "?"
    print(f"  {f[-9:]}: 左上{tag(tl)} 右上{tag(tr)} 左下{tag(bl)} 右下{tag(br)}")
