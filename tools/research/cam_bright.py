# -*- coding: utf-8 -*-
"""在官方摄像头示例副本上，只加「gamma + 增益 + 白平衡」显示侧查表。"""
P = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\project\Titan_Mini_cam_bright\src\hal_entry.c"
lines = open(P, "r", encoding="utf-8", errors="surrogateescape").readlines()

LUT_BLOCK = '''/* ------------------------------------------------------------------
 *  display-side brightening only -- nothing else is changed.
 *  per channel:  x = (v - black) / (max - black)   (0..1)
 *                y = x^GAMMA * GAIN               (gamma < 1 lifts mid-tones)
 *  precomputed once into a 65536-entry RGB565 -> RGB565 table (1 lookup/pixel).
 *  camera registers are deliberately NOT touched: changing AEC/gain there
 *  freezes the video stream on this sensor/port combination.
 * ------------------------------------------------------------------ */
#define TM_BLACK_R   2.0f
#define TM_BLACK_G   5.0f
#define TM_BLACK_B   2.0f
#define TM_GAMMA_R   0.62f
#define TM_GAMMA_G   0.62f
#define TM_GAMMA_B   0.62f
#define TM_GAIN_R    1.06f      /* red WB trims folded in */
#define TM_GAIN_G    0.96f
#define TM_GAIN_B    1.02f

static uint16_t g_tone_lut[65536];

static uint16_t tm_chan(int32_t v, int32_t vmax, float black, float gamma, float gain)
{
    float x = ((float)v - black) / ((float)vmax - black);
    if (x < 0.0f) { x = 0.0f; }
    float y = powf(x, gamma) * gain;
    int32_t o = (int32_t)(y * (float)vmax + 0.5f);
    if (o < 0) { o = 0; }
    if (o > vmax) { o = vmax; }
    return (uint16_t)o;
}

static void tone_lut_build(void)
{
    for (uint32_t c = 0; c < 65536u; c++)
    {
        uint16_t r = tm_chan((int32_t)((c >> 11) & 0x1F), 31, TM_BLACK_R, TM_GAMMA_R, TM_GAIN_R);
        uint16_t g = tm_chan((int32_t)((c >> 5) & 0x3F), 63, TM_BLACK_G, TM_GAMMA_G, TM_GAIN_G);
        uint16_t b = tm_chan((int32_t)(c & 0x1F), 31, TM_BLACK_B, TM_GAMMA_B, TM_GAIN_B);

        g_tone_lut[c] = (uint16_t)((r << 11) | (g << 5) | b);
    }
}

'''

# 1) 插到 DisplayVsyncCallback 之前
i = next(k for k, l in enumerate(lines) if l.startswith("void DisplayVsyncCallback"))
lines.insert(i, LUT_BLOCK)

# 2) 拷贝循环改成查表
i2 = next(k for k, l in enumerate(lines) if "rt_memcpy(p_dest_row, p_src_row, CAMERA_FRAME_LINE_BYTES);" in l)
ind = lines[i2][:len(lines[i2]) - len(lines[i2].lstrip())]
lines[i2] = (ind + "for (int x = 0; x < CAMERA_CAPTURE_IMAGE_WIDTH; x++)\n"
             + ind + "{\n"
             + ind + "    p_dest_row[x] = g_tone_lut[p_src_row[x]];\n"
             + ind + "}\n")

# 3) 启动时建表
i3 = next(k for k, l in enumerate(lines) if "struct rt_device_pwm *pwm12_dev;" in l)
lines.insert(i3, "      tone_lut_build();\n\n")

# 4) 需要 math.h 的 powf
i4 = next(k for k, l in enumerate(lines) if l.startswith("#include"))
lines.insert(i4, "#include <math.h>\n")

open(P, "w", encoding="utf-8", errors="surrogateescape").writelines(lines)
print("gamma tone mapping inserted")
