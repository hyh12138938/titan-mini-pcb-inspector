P = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\project\Titan_Mini_pad_inspect\src\hal_entry.c"
s = open(P, "r", encoding="utf-8", errors="surrogateescape").read()

# 1) 双缓冲状态
anchor = "static void lcd_draw_frame_with_boxes"
assert anchor in s
decl = """/* double buffering: draw into the back buffer, then hand it to GLCDC at frame end */
static uint16_t *s_draw_buf;

static uint16_t *back_buffer(void)
{
    if (s_draw_buf == (uint16_t *)&fb_background[0])
    {
        s_draw_buf = (uint16_t *)&fb_background[1];
    }
    else
    {
        s_draw_buf = (uint16_t *)&fb_background[0];
    }
    return s_draw_buf;
}

"""
s = s.replace(anchor, decl + anchor, 1)

# 2) 用双缓冲绘制
s = s.replace("    d2_framebuffer(hdl, (uint16_t *)&fb_background[0],\n                   LCD_WIDTH, LCD_WIDTH, LCD_HEIGHT, ModeSrc);",
              "    d2_framebuffer(hdl, back_buffer(),\n                   LCD_WIDTH, LCD_WIDTH, LCD_HEIGHT, ModeSrc);", 1)

# 3) 帧末切换 GLCDC 显示的缓冲（下一场同步生效）
old_tail = "    d2_executerenderbuffer(hdl, d2_renderbuffer_get(), 0);\n    d2_flushframe(hdl);"
new_tail = """    d2_executerenderbuffer(hdl, d2_renderbuffer_get(), 0);
    d2_flushframe(hdl);

    /* \u628a\u521a\u753b\u597d\u7684\u540e\u7f13\u51b2\u4ea4\u7ed9 GLCDC\uff0c\u4e0b\u4e00\u573a\u540c\u6b65\u5207\u6362 \u2192 \u6d88\u9664\u6495\u88c2 */
    R_GLCDC_BufferChange(&g_display0_ctrl, (uint8_t *)s_draw_buf, DISPLAY_FRAME_LAYER_1);"""
assert old_tail in s
s = s.replace(old_tail, new_tail, 1)

open(P, "w", encoding="utf-8", errors="surrogateescape").write(s)
print("double buffering applied")
