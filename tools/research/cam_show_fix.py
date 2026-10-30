# -*- coding: utf-8 -*-
"""按行号精确插入「亮度+白平衡」查表，其余保持官方示例原样。"""
P = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\project\Titan_Mini_cam_show\src\hal_entry.c"
lines = open(P, "r", encoding="utf-8", errors="surrogateescape").readlines()

LUT_BLOCK = '''/* ------------------------------------------------------------------
 *  display-side tone mapping only (this is the ONLY change vs the official
 *  camera example): out = clamp((in - black) * gain), white balance folded in.
 *  Precomputed as a 65536-entry RGB565 -> RGB565 table: one lookup per pixel.
 * ------------------------------------------------------------------ */
#define BLACK_R    2           /* of 31 */
#define BLACK_G    6           /* of 63 */
#define BLACK_B    2           /* of 31 */
#define GAIN_R16   36          /* 2.25x, includes red WB  */
#define GAIN_G16   31          /* 1.94x                   */
#define GAIN_B16   32          /* 2.00x, includes blue WB */

static uint16_t g_tone_lut[65536];

static void tone_lut_build(void)
{
    for (uint32_t c = 0; c < 65536u; c++)
    {
        int32_t r = (c >> 11) & 0x1F;
        int32_t g = (c >> 5) & 0x3F;
        int32_t b = c & 0x1F;

        r = (r > BLACK_R) ? (((r - BLACK_R) * GAIN_R16) >> 4) : 0; if (r > 31) r = 31;
        g = (g > BLACK_G) ? (((g - BLACK_G) * GAIN_G16) >> 4) : 0; if (g > 63) g = 63;
        b = (b > BLACK_B) ? (((b - BLACK_B) * GAIN_B16) >> 4) : 0; if (b > 31) b = 31;

        g_tone_lut[c] = (uint16_t)((r << 11) | (g << 5) | b);
    }
}

'''

# 1) 插在 DisplayVsyncCallback 之前
idx = next(i for i, l in enumerate(lines) if l.startswith("void DisplayVsyncCallback"))
lines.insert(idx, LUT_BLOCK)

# 2) 居中 + 查表拷贝
i_off = next(i for i, l in enumerate(lines) if "int x_offset = DISPLAY_SCREEN_WIDTH - CAMERA_CAPTURE_IMAGE_WIDTH;" in l)
indent = lines[i_off][:len(lines[i_off]) - len(lines[i_off].lstrip())]
lines[i_off] = indent + "/* centred 1:1 placement: no scaling, so no moire stripes */\n" \
               + indent + "int x_offset = (DISPLAY_SCREEN_WIDTH - CAMERA_CAPTURE_IMAGE_WIDTH) / 2;\n"

i_cpy = next(i for i, l in enumerate(lines) if "rt_memcpy(p_dest_row, p_src_row, CAMERA_FRAME_LINE_BYTES);" in l)
cind = lines[i_cpy][:len(lines[i_cpy]) - len(lines[i_cpy].lstrip())]
lines[i_cpy] = (cind + "for (int x = 0; x < CAMERA_CAPTURE_IMAGE_WIDTH; x++)\n"
                + cind + "{\n"
                + cind + "    p_dest_row[x] = g_tone_lut[p_src_row[x]];\n"
                + cind + "}\n")

# 3) 启动时建表
i_pwm = next(i for i, l in enumerate(lines) if "struct rt_device_pwm *pwm12_dev;" in l)
lines.insert(i_pwm, "      tone_lut_build();\n\n")

open(P, "w", encoding="utf-8", errors="surrogateescape").writelines(lines)
print("tone mapping inserted (line-based)")
