P = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\project\Titan_Mini_pad_inspect\src\hal_entry.c"
s = open(P, "r", encoding="utf-8", errors="surrogateescape").read()

# 0) 去掉不存在的 d2_setmatrix
s = s.replace("""

    /* the panel is mounted 180 deg rotated w.r.t. the framebuffer (verified with a
       four-quadrant self test), so rotate all drawing by 180 deg here:
       x' = W - x, y' = H - y  (16.16 fixed point) */
    d2_setmatrix(hdl, -(1 << 16), 0, 0, -(1 << 16), (LCD_WIDTH << 16), (LCD_HEIGHT << 16));""", "", 1)

# 1) 旋转缓冲 + 带旋转的提亮
old_fn = s[s.find("static void frame_brighten(uint16_t *fb)"):]
old_fn = old_fn[:old_fn.find("\n}\n") + 3]
new_fn = '''/* rotate 180 deg + apply the display LUT in one pass.
 * the panel is mounted 180 deg rotated (verified by a four-quadrant self test),
 * so we pre-rotate into g_rot and let the panel flip it back to upright. */
static uint16_t g_rot[CAM_WIDTH * CAM_HEIGHT] BSP_ALIGN_VARIABLE(32) BSP_PLACE_IN_SECTION(".sdram");

static void frame_rotate_brighten(const uint16_t *src, uint16_t *dst)
{
    for (int32_t y = 0; y < CAM_HEIGHT; y++)
    {
        const uint16_t *srow = src + (int32_t)(CAM_HEIGHT - 1 - y) * CAM_WIDTH;
        uint16_t *drow = dst + (int32_t)y * CAM_WIDTH;
        for (int32_t x = 0; x < CAM_WIDTH; x++)
        {
            drow[x] = g_disp_lut[srow[(int32_t)(CAM_WIDTH - 1 - x)]];
        }
    }
}
'''
s = s.replace(old_fn, new_fn, 1)

# 2) 调用点
s = s.replace("        frame_brighten(frame);", "        frame_rotate_brighten(frame, g_rot);", 1)
s = s.replace("lcd_draw_frame_with_boxes(frame, CAM_WIDTH, CAM_HEIGHT,",
              "lcd_draw_frame_with_boxes(g_rot, CAM_WIDTH, CAM_HEIGHT,", 1)

# 3) ROI 框坐标镜像（画在镜像位置，屏上才正）
s = s.replace("""        box.x1 = (roi_cx - half) * LCD_WIDTH  / CAM_WIDTH;
        box.y1 = (roi_cy - half) * LCD_HEIGHT / CAM_HEIGHT;
        box.x2 = (roi_cx + half) * LCD_WIDTH  / CAM_WIDTH;
        box.y2 = (roi_cy + half) * LCD_HEIGHT / CAM_HEIGHT;""",
"""        int32_t bx1 = (roi_cx - half) * LCD_WIDTH  / CAM_WIDTH;
        int32_t by1 = (roi_cy - half) * LCD_HEIGHT / CAM_HEIGHT;
        int32_t bx2 = (roi_cx + half) * LCD_WIDTH  / CAM_WIDTH;
        int32_t by2 = (roi_cy + half) * LCD_HEIGHT / CAM_HEIGHT;
        box.x1 = LCD_WIDTH  - bx2;
        box.y1 = LCD_HEIGHT - by2;
        box.x2 = LCD_WIDTH  - bx1;
        box.y2 = LCD_HEIGHT - by1;""", 1)

# 4) 状态方块画到镜像位置（屏上看是左下角）
s = s.replace("d2_renderbox(hdl, D2_FIX(20), D2_FIX(LCD_HEIGHT - 90), D2_FIX(70), D2_FIX(70));",
              "d2_renderbox(hdl, D2_FIX(LCD_WIDTH - 90), D2_FIX(20), D2_FIX(70), D2_FIX(70));", 1)

open(P, "w", encoding="utf-8", errors="surrogateescape").write(s)
print("software 180 rotation applied")
print("  d2_setmatrix left:", "d2_setmatrix" in s)
print("  frame_rotate_brighten:", "frame_rotate_brighten" in s)
