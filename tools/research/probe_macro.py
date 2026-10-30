P = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\project\Titan_Mini_cam_bright\ra_gen\common_data.c"
s = open(P, "r", encoding="utf-8", errors="surrogateescape").read()
s = s.replace('#include "common_data.h"', '''#include "common_data.h"
#pragma message("PROBE GAMMA_R=" _XSTR(GLCDC_CFG_CORRECTION_GAMMA_ENABLE_R) " COLOR=" _XSTR(GLCDC_CFG_COLOR_CORRECTION_ENABLE) " REN=" _XSTR(GLCD_CFG_CORRECTION_GAMMA_ENABLE_R))''', 1)
s = "#define _STR(x) #x\n#define _XSTR(x) _STR(x)\n" + s
open(P, "w", encoding="utf-8", errors="surrogateescape").write(s)
print("probe inserted")
