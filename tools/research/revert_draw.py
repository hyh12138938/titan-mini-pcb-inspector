P = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\project\Titan_Mini_pad_inspect\src\hal_entry.c"
s = open(P, "r", encoding="utf-8", errors="surrogateescape").read()

# 1) 撤销双缓冲：删除 back_buffer 块
i0 = s.find("/* double buffering: draw into the back buffer")
i1 = s.find("static void lcd_draw_frame_with_boxes")
assert i0 != -1 and i1 > i0
s = s[:i0] + s[i1:]

# 2) 画到固定前台缓冲
s = s.replace("    d2_framebuffer(hdl, back_buffer(),", "    d2_framebuffer(hdl, (uint16_t *)&fb_background[0],", 1)

# 3) 去掉整屏填黑
s = s.replace("    d2_setcolor(hdl, 0, 0xFF000000u);\n    d2_renderbox(hdl, D2_FIX(0), D2_FIX(0), D2_FIX(LCD_WIDTH), D2_FIX(LCD_HEIGHT));\n", "", 1)

# 4) blit 恢复为铺满整屏（撤销 1:1）
s = s.replace("""    /* 1:1 灞呬腑锛屼笉鍋?640->800 缂╂斁锛堝惁鍒欎細鍑虹幇 5px 鍛ㄦ湡鐨勭旱鍚戞懜灏旇汗锛?*/
    d2_blitcopy(hdl, xSize, ySize, 0, 0,
                D2_FIX(xSize), D2_FIX(ySize),
                D2_FIX(FB_XOFF), D2_FIX(FB_YOFF), 0);""",
"""    d2_blitcopy(hdl, xSize, ySize, 0, 0,
                D2_FIX(LCD_WIDTH), D2_FIX(LCD_HEIGHT),
                D2_FIX(0), D2_FIX(0), 0);""", 1)

# 5) 去掉帧末 BufferChange
s = s.replace("""
    /* 鎶婂垰鐢诲ソ鐨勫悗缂撳啿浜ょ粰 GLCDC锛屼笅涓€鍦哄悓姝ュ垏鎹?-> 娑堥櫎鎾曡",
                "", 1)
import re
s = re.sub(r"\n\s*/\*[^\n]*GLCDC[^\n]*\*/\n\s*R_GLCDC_BufferChange\([^;]*\);\n", "\n", s)

# 6) ROI 框坐标恢复为按比例缩放
s = s.replace("""        box.x1 = FB_XOFF + (roi_cx - half);
        box.y1 = FB_YOFF + (roi_cy - half);
        box.x2 = FB_XOFF + (roi_cx + half);
        box.y2 = FB_YOFF + (roi_cy + half);""",
"""        box.x1 = (roi_cx - half) * LCD_WIDTH  / CAM_WIDTH;
        box.y1 = (roi_cy - half) * LCD_HEIGHT / CAM_HEIGHT;
        box.x2 = (roi_cx + half) * LCD_WIDTH  / CAM_WIDTH;
        box.y2 = (roi_cy + half) * LCD_HEIGHT / CAM_HEIGHT;""", 1)

# 7) 逐像素运算 -> 64K 查表
i2 = s.find("/* display-side processing")
i3 = s.find("static void build_pix_lut(void)")
assert i2 != -1 and i3 > i2
lut_block = '''/* display-side processing, done through a 64K RGB565 -> RGB565 lookup table
 * (single table lookup per pixel: cheap enough to keep the frame rate up).
 * Transform: out = clamp((in - black) * gain), per channel, WB folded into gains.
 */
#define BLACK_R    2           /* of 31 */
#define BLACK_G    6           /* of 63 */
#define BLACK_B    2           /* of 31 */
#define GAIN_R16   36          /* 2.25x, includes +12% red WB */
#define GAIN_G16   31          /* 1.94x */
#define GAIN_B16   32          /* 2.00x, includes +3% blue WB */

static uint16_t g_disp_lut[65536] BSP_ALIGN_VARIABLE(32) BSP_PLACE_IN_SECTION(".sdram");

static void build_disp_lut(void)
{
    for (uint32_t c = 0; c < 65536u; c++)
    {
        int32_t r = (c >> 11) & 0x1F;
        int32_t g = (c >> 5) & 0x3F;
        int32_t b = c & 0x1F;

        r = (r > BLACK_R) ? (((r - BLACK_R) * GAIN_R16) >> 4) : 0; if (r > 31) r = 31;
        g = (g > BLACK_G) ? (((g - BLACK_G) * GAIN_G16) >> 4) : 0; if (g > 63) g = 63;
        b = (b > BLACK_B) ? (((b - BLACK_B) * GAIN_B16) >> 4) : 0; if (b > 31) b = 31;

        g_disp_lut[c] = (uint16_t)((r << 11) | (g << 5) | b);
    }
}

static void frame_brighten(uint16_t *fb)
{
    uint32_t n = (uint32_t)CAM_WIDTH * CAM_HEIGHT;
    for (uint32_t i = 0; i < n; i++)
    {
        fb[i] = g_disp_lut[fb[i]];
    }
}

'''
s = s[:i2] + lut_block + s[i3:]

# 8) 初始化 LUT
s = s.replace("    build_pix_lut();", "    build_pix_lut();\n    build_disp_lut();", 1)

open(P, "w", encoding="utf-8", errors="surrogateescape").write(s)
print("reverted to single-buffer stretch + 64K LUT")
print("has back_buffer:", "back_buffer" in s)
print("has BufferChange:", "R_GLCDC_BufferChange" in s)
print("has FB_XOFF blit:", "D2_FIX(xSize), D2_FIX(ySize)" in s)
