P = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\project\Titan_Mini_cam_bright\src\hal_entry.c"
lines = open(P, "r", encoding="utf-8", errors="surrogateescape").readlines()

# 1) 去掉探针宏
txt = "".join(lines)
txt = txt.replace('#pragma message("PROBE GAMMA_R=" _XSTR(GLCD_CFG_CORRECTION_GAMMA_ENABLE_R) " COLOR=" _XSTR(GLCD_CFG_COLOR_CORRECTION_ENABLE) " REN=" _XSTR(GLCD_CFG_CORRECTION_GAMMA_ENABLE_R))', "")
txt = txt.replace("#define _STR(x) #x\n#define _XSTR(x) _STR(x)\n", "")
lines = txt.splitlines(keepends=True)

# 2) 插 D2 函数（在 DisplayVsyncCallback 之前）
helper = '''/* ---- hardware brightening: DAVE2D additive blits (no CPU cost) ---- */
#define D2_BRIGHT_PASSES   2       /* 1 = off, 2 = ~2x, 3 = ~3x */

#ifndef D2_FIX
#define D2_FIX(px)  ((d2_point)((px) << 4))
#endif

static void d2_brighten_overlay(d2_device *hdl, const uint16_t *src,
                                int32_t srcw, int32_t srch,
                                uint16_t *dst, int32_t dstw, int32_t dsth,
                                int32_t x_off, int32_t y_off)
{
    d2_framebuffer(hdl, dst, dstw, dstw, dsth, d2_mode_rgb565);
    d2_selectrenderbuffer(hdl, d2_renderbuffer_get());
    d2_cliprect(hdl, 0, 0, dstw, dsth);
    d2_setblitsrc(hdl, (void *)src, srcw, srcw, srch, d2_mode_rgb565);

    d2_setblendmode(hdl, d2_bm_one, d2_bm_one);   /* additive */
    for (int i = 1; i < D2_BRIGHT_PASSES; i++)
    {
        d2_blitcopy(hdl, srcw, srch, 0, 0,
                    D2_FIX(srcw), D2_FIX(srch), D2_FIX(x_off), D2_FIX(y_off), 0);
    }
    /* white balance nudge (additive tint) */
    d2_setcolor(hdl, 0, 0xFF100408u);
    d2_renderbox(hdl, D2_FIX(x_off), D2_FIX(y_off), D2_FIX(srcw), D2_FIX(srch));

    d2_setblendmode(hdl, d2_bm_alpha, d2_bm_one_minus_alpha);
    d2_executerenderbuffer(hdl, d2_renderbuffer_get(), 0);
    d2_flushframe(hdl);
}

'''
i = next(k for k, l in enumerate(lines) if l.startswith("void DisplayVsyncCallback"))
lines.insert(i, helper)

# 3) 在行循环结束后调用（memcpy 后面那个 '}' 之后）
i_mem = next(k for k, l in enumerate(lines) if "rt_memcpy(p_dest_row, p_src_row, CAMERA_FRAME_LINE_BYTES);" in l)
# 找 memcpy 之后第一个仅含 '}' 的行（行循环结束）
j = i_mem + 1
while j < len(lines) and lines[j].strip() != "}":
    j += 1
indent = " " * 10
call = (indent + "d2_device *hdl_d2 = d2_handle_obj_get();\n"
        + indent + "if (NULL != hdl_d2)\n"
        + indent + "{\n"
        + indent + "    d2_brighten_overlay(hdl_d2, p_src,\n"
        + indent + "                        CAMERA_CAPTURE_IMAGE_WIDTH, CAMERA_CAPTURE_IMAGE_HEIGHT,\n"
        + indent + "                        p_dest, DISPLAY_SCREEN_WIDTH, DISPLAY_SCREEN_HEIGHT,\n"
        + indent + "                        x_offset, 0);\n"
        + indent + "}\n")
lines.insert(j + 1, call)

open(P, "w", encoding="utf-8", errors="surrogateescape").writelines(lines)
print("inserted at line", j + 2)
