P = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\project\Titan_Mini_pad_inspect\src\hal_entry.c"
s = open(P, "r", encoding="utf-8", errors="surrogateescape").read()

old_start = s.find("#define DISP_GAIN16")
old_end   = s.find("static void build_pix_lut(void)")
assert old_start != -1 and old_end != -1 and old_end > old_start

new_block = '''/* 显示侧处理（不进入模型输入）：
 *   1) 亮度增益 2.0x
 *   2) 单通道白平衡：实测白纸 G 比 R 高 13%%、B 高 4%%，这里把 R/B 补回来
 * 16 = 1.0x
 */
#define GAIN_G16   32          /* 2.00x */
#define GAIN_R16   36          /* 2.25x = 2.00 * 1.125 */
#define GAIN_B16   33          /* 2.06x = 2.00 * 1.03  */

static void frame_brighten(uint16_t *fb)
{
    uint32_t n = (uint32_t)CAM_WIDTH * CAM_HEIGHT;
    for (uint32_t i = 0; i < n; i++)
    {
        uint16_t c = fb[i];
        int32_t r = (c >> 11) & 0x1F;
        int32_t g = (c >> 5) & 0x3F;
        int32_t b = c & 0x1F;

        r = (r * GAIN_R16) >> 4; if (r > 31) r = 31;
        g = (g * GAIN_G16) >> 4; if (g > 63) g = 63;
        b = (b * GAIN_B16) >> 4; if (b > 31) b = 31;

        fb[i] = (uint16_t)((r << 11) | (g << 5) | b);
    }
}

'''
s = s[:old_start] + new_block + s[old_end:]
open(P, "w", encoding="utf-8", errors="surrogateescape").write(s)
print("per-channel WB applied")
