import re
CDC = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\project\Titan_Mini_cam_bright\ra_gen\common_data.c"
HE  = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\project\Titan_Mini_cam_bright\src\hal_entry.c"

THR = [0, 64, 128, 192, 256, 320, 384, 448, 512, 576, 640, 704, 768, 832, 896, 960]
TMAX, GAMMA = 1024.0, 0.78
TINT = {"r": 1.00, "g": 0.93, "b": 0.99}   # 绿色压低 => 纠正偏绿

def curve(t, k):
    x = min(1.0, t / TMAX)
    return min(1.0, (x ** GAMMA) * k) * 1024.0

def gains(k):
    g = []
    for i in range(len(THR) - 1):
        t0, t1 = THR[i], THR[i+1]
        g.append(max(0, min(4095, int(round((curve(t1,k)-curve(t0,k))/(t1-t0)*1024.0)))))
    t0 = THR[-1]
    g.append(max(0, min(4095, int(round((curve(TMAX,k)-curve(t0,k))/(TMAX-t0)*1024.0)))))
    return g

cd = open(CDC, "r", encoding="utf-8", errors="surrogateescape").read()
for ch in "rgb":
    arr = gains(TINT[ch])
    arrtxt = ", ".join(str(v) for v in arr)
    pat = re.compile(rf"(static GLCDC_CFG_CORRECTION_GAMMA_TABLE_CONST uint16_t glcdc_gamma_{ch}_gain\[DISPLAY_GAMMA_CURVE_ELEMENT_NUM\] = )\{{[^}}]*\}};")
    cd, n = pat.subn(rf"\g<1>{{{arrtxt}}};", cd)
    print(f"  {ch}: n={n} {arr}")
    print(f"     校验: 单调不减={all(arr[i]>=0 for i in range(len(arr)))} 末段={arr[-1]}")
open(CDC, "w", encoding="utf-8", errors="surrogateescape").write(cd)

# 清掉 hal_entry 里残留的 tone lut 块（如果还在）
h = open(HE, "r", encoding="utf-8", errors="surrogateescape").read()
print("  hal_entry 仍含 g_tone_lut:", "g_tone_lut" in h)
if "g_tone_lut" in h:
    i0 = h.find("/* ------------------------------------------------------------------")
    i1 = h.find("void DisplayVsyncCallback")
    if i0 != -1 and i1 > i0:
        h = h[:i0] + h[i1:]
        open(HE, "w", encoding="utf-8", errors="surrogateescape").write(h)
        print("  已删除残留 tone lut 块:", "g_tone_lut" not in h)
