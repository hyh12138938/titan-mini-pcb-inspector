import numpy as np
from PIL import Image
p = r"C:\Users\hyh7758521\.dsh\attachments\v1\objects\cd\cd82a7eaf36f346ca92b17005787f28b1dbd4d37a57542935c4e56d7730ad32e"
im = Image.open(p).convert("RGB")
# 只取面板内部（按目测裁剪，留边）
X0,Y0,X1,Y1 = 330, 310, 830, 1150
crop = im.crop((X0,Y0,X1,Y1))
crop.save(r"D:\RTT\_re\shots\f_panel.png")
a = np.asarray(crop).astype(np.float32)
h,w,_ = a.shape
print(f"  面板裁剪 {w}x{h}")
r,g,b = a[...,0],a[...,1],a[...,2]
red = (r>140)&(g<100)&(b<100)
grn = (g>150)&(r<140)&(b<140)
wht = (r>150)&(g>150)&(b>150)
def cen(m,name):
    ys,xs=np.nonzero(m)
    if len(xs)<50: print(f"  {name}: 太少({len(xs)})"); return None
    cx,cy=xs.mean(),ys.mean()
    print(f"  {name}: 质心=({cx/w:+.2f},{cy/h:+.2f}) 归一化 面积={len(xs)}")
    return (cx/w, cy/h)
cr=cen(red,"红块"); cg=cen(grn,"绿块")
ys,xs=np.nonzero(wht)
if len(xs)>200:
    X=np.stack([xs-xs.mean(), ys-ys.mean()],axis=1)
    cov=X.T@X/len(X); wv,v=np.linalg.eigh(cov)
    ax=v[:,np.argmax(wv)]
    ang=np.degrees(np.arctan2(ax[1],ax[0]))%180
    print(f"  F 主方向={ang:.1f}°  包围盒={xs.max()-xs.min()+1}x{ys.max()-ys.min()+1} 面积={len(xs)}")
    print(f"  F 质心归一化=({xs.mean()/w:+.2f},{ys.mean()/h:+.2f})")
