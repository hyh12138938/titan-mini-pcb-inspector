import io
ROOT = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\FSPConfiguration"
# 1) 头文件：打开 gamma 使能
p = ROOT + r"\ra_gen\common_data.h"
s = open(p, "r", encoding="utf-8", errors="surrogateescape").read()
for ch in "RGB":
    for old in (f"GLCDC_CFG_CORRECTION_GAMMA_ENABLE_{ch}       (false)",
                f"GLCDC_CFG_CORRECTION_GAMMA_ENABLE_{ch}      (false)",
                f"GLCDC_CFG_CORRECTION_GAMMA_ENABLE_{ch}     (false)"):
        s = s.replace(old, old.replace("(false)", "(true)"))
open(p, "w", encoding="utf-8", errors="surrogateescape").write(s)
print("  SDK common_data.h:", [l.strip() for l in s.splitlines() if "GAMMA_ENABLE_R" in l or "GAMMA_ENABLE_G" in l or "GAMMA_ENABLE_B" in l])

# 2) 源文件：把 gamma 增益数组改成提亮曲线（若 SDK 版本被使用）
import re
p2 = ROOT + r"\ra_gen\common_data.c"
c = open(p2, "r", encoding="utf-8", errors="surrogateescape").read()
THR = [0,64,128,192,256,320,384,448,512,576,640,704,768,832,896,960]
TMAX, GAMMA, CAP = 1024.0, 0.45, 4095
TINT = {"r":1.00,"g":0.94,"b":0.99}
def curve(t,k):
    x=min(1.0,t/TMAX); return min(1.0,(x**GAMMA)*k)*1024.0
def gains(k):
    g=[]
    for i in range(len(THR)-1):
        t0,t1=THR[i],THR[i+1]
        g.append(max(0,min(CAP,int(round((curve(t1,k)-curve(t0,k))/(t1-t0)*1024.0)))))
    t0=THR[-1]
    g.append(max(0,min(CAP,int(round((curve(TMAX,k)-curve(t0,k))/(TMAX-t0)*1024.0)))))
    return g
for ch in "rgb":
    arr=", ".join(str(v) for v in gains(TINT[ch]))
    pat=re.compile(rf"(static GLCDC_CFG_CORRECTION_GAMMA_TABLE_CONST uint16_t glcdc_gamma_{ch}_gain\[DISPLAY_GAMMA_CURVE_ELEMENT_NUM\] = )\s*\{{[^}}]*\}};", re.S)
    c,n=pat.subn(rf"\g<1>{arr}}};", c)
    print(f"  SDK common_data.c gamma_{ch}: replaced={n}")
open(p2,"w",encoding="utf-8",errors="surrogateescape").write(c)
