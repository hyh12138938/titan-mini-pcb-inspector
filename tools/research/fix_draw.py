# -*- coding: utf-8 -*-
"""按行精确替换：撤销双缓冲/整屏填黑/1:1，改为 64K 查表提亮。"""
P = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\project\Titan_Mini_pad_inspect\src\hal_entry.c"

with open(P, "r", encoding="utf-8", errors="surrogateescape") as f:
    lines = f.readlines()

def find(pred, start=0):
    for i in range(start, len(lines)):
        if pred(lines[i]):
            return i
    return -1

# ---- 1) brighten 段：从 "/* display-side processing" 到 "static void build_pix_lut" ----
a = find(lambda l: l.startswith("/* display-side processing"))
b = find(lambda l: l.startswith("static void build_pix_lut"))
assert a != -1 and b != -1 and b > a, (a, b)

new_brighten = '''/* 显示侧处理：64K RGB565->RGB565 查表（每像素一次查表，足够快，不拖帧率）
 * out = clamp((in - black) * gain)，逐通道，白平衡已折进 gain
 */
#define BLACK_R    2           /* of 31 */
#define BLACK_G    6           /* of 63 */
#define BLACK_B    2           /* of 31 */
#define GAIN_R16   36          /* 2.25x，含 +12% 红 */
#define GAIN_G16   31          /* 1.94x */
#define GAIN_B16   32          /* 2.00x，含 +3% 蓝 */

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
lines[a:b] = [new_brighten]

# ---- 2) 双缓冲 + 绘制函数：从 "/* double buffering" 到 "static int cmd_roi" ----
a = find(lambda l: l.startswith("/* double buffering"))
b = find(lambda l: l.startswith("static int cmd_roi"))
assert a != -1 and b != -1 and b > a, (a, b)

new_draw = '''/* 单缓冲直接绘制（与能出图的版本一致），避免双缓冲切换带来的卡顿 */
static void lcd_draw_frame_with_boxes(const void *p, int32_t xSize, int32_t ySize,
                                      uint32_t argb, int32_t thickness,
                                      pad_box_t *boxes, int32_t box_num,
                                      int32_t fill_ok, uint32_t fill_argb)
{
    if (thickness < 1)
    {
        thickness = 1;
    }

    uint32_t ModeSrc = d2_mode_rgb565;
    d2_device *hdl = d2_handle_obj_get();

    d2_framebuffer(hdl, (uint16_t *)&fb_background[0],
                   LCD_WIDTH, LCD_WIDTH, LCD_HEIGHT, ModeSrc);

    d2_selectrenderbuffer(hdl, d2_renderbuffer_get());
    d2_cliprect(hdl, 0, 0, LCD_WIDTH, LCD_HEIGHT);

    d2_setblitsrc(hdl, (void *)p, xSize, xSize, ySize, ModeSrc);
    d2_blitcopy(hdl, xSize, ySize, 0, 0,
                D2_FIX(LCD_WIDTH), D2_FIX(LCD_HEIGHT),
                D2_FIX(0), D2_FIX(0), 0);

    /* 左下角状态方块：红=检测到焊盘，灰=没有 */
    if (fill_ok)
    {
        d2_setcolor(hdl, 0, fill_argb);
        d2_renderbox(hdl, D2_FIX(20), D2_FIX(LCD_HEIGHT - 90), D2_FIX(70), D2_FIX(70));
    }

    d2_setcolor(hdl, 0, argb);
    d2_width draw_thickness = D2_FIX(thickness);
    d2_u32 flags = d2_le_exclude_none;

    for (int i = 0; i < box_num; i++, boxes++)
    {
        d2_point x1 = D2_FIX(boxes->x1);
        d2_point y1 = D2_FIX(boxes->y1);
        d2_point x2 = D2_FIX(boxes->x2);
        d2_point y2 = D2_FIX(boxes->y2);

        d2_renderline(hdl, x1, y1, x2, y1, draw_thickness, flags);
        d2_renderline(hdl, x1, y1, x1, y2, draw_thickness, flags);
        d2_renderline(hdl, x2, y1, x2, y2, draw_thickness, flags);
        d2_renderline(hdl, x1, y2, x2, y2, draw_thickness, flags);
    }

    d2_executerenderbuffer(hdl, d2_renderbuffer_get(), 0);
    d2_flushframe(hdl);
}

'''
lines[a:b] = [new_draw]

# ---- 3) ROI 框坐标恢复按比例 ----
txt = "".join(lines)
old_box = """        box.x1 = FB_XOFF + (roi_cx - half);"""
if old_box in txt:
    import re
    txt = re.sub(r"\s*box\.x1 = FB_XOFF \+ \(roi_cx - half\);\s*\n\s*box\.y1 = FB_YOFF \+ \(roi_cy - half\);\s*\n\s*box\.x2 = FB_XOFF \+ \(roi_cx \+ half\);\s*\n\s*box\.y2 = FB_YOFF \+ \(roi_cy \+ half\);",
                 """
        box.x1 = (roi_cx - half) * LCD_WIDTH  / CAM_WIDTH;
        box.y1 = (roi_cy - half) * LCD_HEIGHT / CAM_HEIGHT;
        box.x2 = (roi_cx + half) * LCD_WIDTH  / CAM_WIDTH;
        box.y2 = (roi_cy + half) * LCD_HEIGHT / CAM_HEIGHT;""", txt)

# ---- 4) 初始化查表 ----
if "build_disp_lut();" not in txt:
    txt = txt.replace("    build_pix_lut();", "    build_pix_lut();\n    build_disp_lut();", 1)

with open(P, "w", encoding="utf-8", errors="surrogateescape") as f:
    f.write(txt)

print("ok; has back_buffer:", "back_buffer" in txt,
      "| has BufferChange:", "R_GLCDC_BufferChange" in txt,
      "| has FB_XOFF box:", "FB_XOFF + (roi_cx" in txt,
      "| lamp:")
