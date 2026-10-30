import re
CDC = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\project\Titan_Mini_cam_bright\ra_gen\common_data.c"
THR = [0, 64, 128, 192, 256, 320, 384, 448, 512, 576, 640, 704, 768, 832, 896, 960]
TMAX, GAMMA, CAP = 1024.0, 0.45, 4095
TINT = {"r": 1.00, "g": 0.94, "b": 0.99}

def curve(t, k):
    x = min(1.0, t / TMAX)
    return min(1.0, (x ** GAMMA) * k) * 1024.0

def gains(k):
    g = []
    for i in range(len(THR) - 1):
        t0, t1 = THR[i], THR[i+1]
        g.append(max(0, min(CAP, int(round((curve(t1,k)-curve(t0,k))/(t1-t0)*1024.0)))))
    t0 = THR[-1]
    g.append(max(0, min(CAP, int(round((curve(TMAX,k)-curve(t0,k))/(TMAX-t0)*1024.0)))))
    return g

cd = open(CDC, "r", encoding="utf-8", errors="surrogateescape").read()
for ch in "rgb":
    arr = gains(TINT[ch]); arrtxt = ", ".join(str(v) for v in arr)
    pat = re.compile(rf"(static GLCDC_CFG_CORRECTION_GAMMA_TABLE_CONST uint16_t glcdc_gamma_{ch}_gain\[DISPLAY_GAMMA_CURVE_ELEMENT_NUM\] = )\{{[^}}]*\}};")
    cd, n = pat.subn(rf"\g<1>{{{arrtxt}}};", cd)
    print(f"  {ch}: n={n}")
    print(f"     {arr}")
    # 预期输出映射（以 0..1024 输入）
    for t in (64, 128, 256, 512, 768, 1024):
        y = curve(t, TINT[ch])
        print(f"     in {t:4d} -> out {y:6.0f}  ({y/1024*255:5.1f}/255)")
open(CDC, "w", encoding="utf-8", errors="surrogateescape").write(cd)
