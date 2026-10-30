P = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\project\Titan_Mini_pad_inspect\src\hal_entry.c"
s = open(P, "r", encoding="utf-8", errors="surrogateescape").read()
start = s.find("/* \u663e\u793a\u4fa7\u5904\u7406")
end   = s.find("static void build_pix_lut(void)")
assert start != -1 and end > start

new = '''/* display-side processing (never touches model input):
 *   out = clamp((in - black) * gain)  per channel, with WB folded in.
 *   black point removes the haze, gain lifts the rest, clip keeps highlights sane.
 * 16 = 1.0x
 */
#define BLACK_R    3           /* of 31 */
#define BLACK_G    7           /* of 63 */
#define BLACK_B    3           /* of 31 */
#define GAIN_R16   34          /* 2.13x incl. +19% red WB */
#define GAIN_G16   29          /* 1.81x */
#define GAIN_B16   30          /* 1.88x incl. +3% blue WB */

static void frame_brighten(uint16_t *fb)
{
    uint32_t n = (uint32_t)CAM_WIDTH * CAM_HEIGHT;
    for (uint32_t i = 0; i < n; i++)
    {
        uint16_t c = fb[i];
        int32_t r = (c >> 11) & 0x1F;
        int32_t g = (c >> 5) & 0x3F;
        int32_t b = c & 0x1F;

        r = (r > BLACK_R) ? (((r - BLACK_R) * GAIN_R16) >> 4) : 0; if (r > 31) r = 31;
        g = (g > BLACK_G) ? (((g - BLACK_G) * GAIN_G16) >> 4) : 0; if (g > 63) g = 63;
        b = (b > BLACK_B) ? (((b - BLACK_B) * GAIN_B16) >> 4) : 0; if (b > 31) b = 31;

        fb[i] = (uint16_t)((r << 11) | (g << 5) | b);
    }
}

'''
s = s[:start] + new + s[end:]
open(P, "w", encoding="utf-8", errors="surrogateescape").write(s)
print("level-stretch applied")
