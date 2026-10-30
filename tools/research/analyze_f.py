import numpy as np
from PIL import Image
im = Image.open(r"C:\Users\hyh7758521\.dsh\attachments\v1\objects\cd\cd82a7eaf36f346ca92b17005787f28b1dbd4d37a57542935c4e56d7730ad32e")
a = np.asarray(im.convert("RGB")).astype(np.float32)
H,W,_ = a.shape
r,g,b = a[...,0], a[...,1], a[...,2]
# 面板区域：找亮度较高的矩形块（面板比绿色桌面亮）
lum = a.mean(axis=2)
mask_panel = lum > 40
ys,xs = np.nonzero(mask_panel)
print(f"  图像 {W}x{H}")
# 红色/绿色标记
red  = (r>140)&(g<90)&(b<90)
grn  = (g>140)&(r<120)&(b<120)
wht  = (r>170)&(g>170)&(b>170)
def cen(m, name):
    ys,xs = np.nonzero(m)
    if len(xs)==0: print(f"  {name}: 未找到"); return None
    cx,cy = xs.mean(), ys.mean()
    print(f"  {name}: 质心=({cx:.0f},{cy:.0f}) 面积={len(xs)} 范围x[{xs.min()}-{xs.max()}] y[{ys.min()}-{ys.max()}]")
    return (cx,cy,len(xs))
cr = cen(red,"红块"); cg = cen(grn,"绿块"); cw = cen(wht,"白字母F")
if cw:
    ys,xs = np.nonzero(wht)
    # PCA 主轴
    X = np.stack([xs-xs.mean(), ys-ys.mean()],axis=1)
    cov = X.T@X/len(X)
    w,v = np.linalg.eigh(cov)
    axis = v[:, np.argmax(w)]
    ang = np.degrees(np.arctan2(axis[1], axis[0])) % 180
    print(f"  白字母主方向 = {ang:.1f}°  (0=水平, 90=垂直)")
    print(f"  白字母包围盒 = {xs.max()-xs.min()+1} x {ys.max()-ys.min()+1}")
