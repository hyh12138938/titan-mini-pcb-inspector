# -*- coding: utf-8 -*-
"""撤掉逐像素查表，改用 GLCDC 硬件 gamma 校正提亮。"""
import re

PROJ = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\project\Titan_Mini_cam_bright"
HE = PROJ + r"\src\hal_entry.c"
CDH = PROJ + r"\ra_gen\common_data.h"
CDC = PROJ + r"\ra_gen\common_data.c"
CFG = PROJ + r"\ra_cfg\fsp_cfg\r_glcdc_cfg.h"

# ---------------- 1) 撤掉逐像素查表，恢复 memcpy ----------------
lines = open(HE, "r", encoding="utf-8", errors="surrogateescape").readlines()
out, skip = [], False
for l in lines:
    if l.startswith("/* ------------------------------------------------------------------") and not skip:
        # 可能是 tone 块或别的注释块，先探测后面几行
        pass
    out.append(l)

txt = "".join(out)
# 删掉 tone lut 块（从注释标题到 tone_lut_build 结束）
m = re.search(r"/\* -+\n \*  display-side brightening only.*?\n\}\n\n", txt, re.S)
if m:
    txt = txt[:m.start()] + txt[m.end():]
# 恢复 memcpy
txt = re.sub(r"for \(int x = 0; x < CAMERA_CAPTURE_IMAGE_WIDTH; x\+\+\)\s*\n\s*\{\s*\n\s*p_dest_row\[x\] = g_tone_lut\[p_src_row\[x\]\];\s*\n\s*\}\n",
             "rt_memcpy(p_dest_row, p_src_row, CAMERA_FRAME_LINE_BYTES);\n", txt)
# 去掉 tone_lut_build() 调用和 math.h
txt = txt.replace("      tone_lut_build();\n\n", "")
txt = txt.replace("#include <math.h>\n", "")
open(HE, "w", encoding="utf-8", errors="surrogateescape").write(txt)
print("hal_entry: memcpy restored =", "rt_memcpy(p_dest_row" in txt,
      "| tone lut removed =", "g_tone_lut" not in txt)

# ---------------- 2) 打开硬件颜色/伽马校正 ----------------
c = open(CFG, "r", encoding="utf-8", errors="surrogateescape").read()
c = c.replace("#define GLCDC_CFG_COLOR_CORRECTION_ENABLE (false)",
              "#define GLCDC_CFG_COLOR_CORRECTION_ENABLE (true)")
open(CFG, "w", encoding="utf-8", errors="surrogateescape").write(c)
print("color correction enabled =", "COLOR_CORRECTION_ENABLE (true)" in c)

h = open(CDH, "r", encoding="utf-8", errors="surrogateescape").read()
for ch in "RGB":
    h = h.replace(f"#define GLCDC_CFG_CORRECTION_GAMMA_ENABLE_{ch}       (false)",
                  f"#define GLCDC_CFG_CORRECTION_GAMMA_ENABLE_{ch}       (true)")
    h = h.replace(f"#define GLCDC_CFG_CORRECTION_GAMMA_ENABLE_{ch}      (false)",
                  f"#define GLCDC_CFG_CORRECTION_GAMMA_ENABLE_{ch}      (true)")
open(CDH, "w", encoding="utf-8", errors="surrogateescape").write(h)
print("gamma enables:", [f"{ch}={'true' if f'GAMMA_ENABLE_{ch}       (true)' in h or f'GAMMA_ENABLE_{ch}      (true)' in h else 'false'}" for ch in "RGB"])

# ---------------- 3) 生成伽马增益表 ----------------
THR = [0, 64, 128, 192, 256, 320, 384, 448, 512, 576, 640, 704, 768, 832, 896, 960]
TMAX = 1024.0
GAMMA = 0.72
WB = {"R": 1.06, "G": 0.97, "B": 1.02}


def curve(t, wb):
    x = min(1.0, t / TMAX)
    y = (x ** GAMMA) * wb
    return min(1.0, y) * 1024.0


def gains(wb):
    g = []
    for i in range(len(THR) - 1):
        t0, t1 = THR[i], THR[i + 1]
        slope = (curve(t1, wb) - curve(t0, wb)) / (t1 - t0)
        val = int(round(slope * 1024.0))
        g.append(max(0, min(4095, val)))
    # 最后一段 [960,1024)
    t0 = THR[-1]
    slope = (curve(TMAX, wb) - curve(t0, wb)) / (TMAX - t0)
    g.append(max(0, min(4095, int(round(slope * 1024.0)))))
    return g


cd = open(CDC, "r", encoding="utf-8", errors="surrogateescape").read()
for ch in "rgb":
    arr = gains(WB[ch.upper()])
    arrtxt = ", ".join(str(v) for v in arr)
    pat = re.compile(rf"(static GLCDC_CFG_CORRECTION_GAMMA_TABLE_CONST uint16_t glcdc_gamma_{ch}_gain\[DISPLAY_GAMMA_CURVE_ELEMENT_NUM\] = )\{{[^}}]*\}};")
    cd, n = pat.subn(rf"\g<1>{{{arrtxt}}};", cd)
    print(f"  gamma_{ch}_gain replaced: {n}  -> {arr}")

open(CDC, "w", encoding="utf-8", errors="surrogateescape").write(cd)
print("done")
