# -*- coding: utf-8 -*-
"""把 memcpy 换成 DAVE2D 叠加 blit：画面叠加 EXTRA_PASSES 次 => 硬件提亮，无 CPU 开销。"""
P = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\project\Titan_Mini_cam_bright\src\hal_entry.c"
s = open(P, "r", encoding="utf-8", errors="surrogateescape").read()

# 去掉探针
s = s.replace('#pragma message("PROBE GAMMA_R=" _XSTR(GLCD_CFG_CORRECTION_GAMMA_ENABLE_R) " COLOR=" _XSTR(GLCD_CFG_COLOR_CORRECTION_ENABLE) " REN=" _XSTR(GLCD_CFG_CORRECTION_GAMMA_ENABLE_R))', "")
s = s.replace("#define _STR(x) #x\n#define _XSTR(x) _STR(x)\n", "")

# 1) 在 DisplayVsyncCallback 之前插入 D2_FIX 宏与叠加函数
anchor = "void DisplayVsyncCallback(display_callback_args_t * p_args)"
assert anchor in s
helper = '''/* ---- hardware brightening via DAVE2D additive blits (no CPU cost) ---- */
#define D2_BRIGHT_PASSES   2       /* 1 = off, 2 = ~2x, 3 = ~3x (clipped) */

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

    /* additive: dst = dst + src  (first pass already copied by memcpy) */
    d2_setblendmode(hdl, d2_bm_one, d2_bm_one);
    for (int i = 1; i < D2_BRIGHT_PASSES; i++)
    {
        d2_blitcopy(hdl, srcw, srch, 0, 0,
                    D2_FIX(srcw), D2_FIX(srch),
                    D2_FIX(x_off), D2_FIX(y_off), 0);
    }
    /* white-balance tint: add a little red, take nothing from blue */
    d2_setcolor(hdl, 0, 0xFF100408u);   /* ARGB: +16 red, +4 green, +8 blue */
    d2_renderbox(hdl, D2_FIX(x_off), D2_FIX(y_off), D2_FIX(srcw), D2_FIX(srch));

    d2_setblendmode(hdl, d2_bm_alpha, d2_bm_one_minus_alpha);
    d2_executerenderbuffer(hdl, d2_renderbuffer_get(), 0);
    d2_flushframe(hdl);
}

'''
s = s.replace(anchor, helper + anchor, 1)

# 2) memcpy 之后调用叠加
old = "              rt_memcpy(p_dest_row, p_src_row, CAMERA_FRAME_LINE_BYTES);\n          }"
assert old in s, "memcpy 位置未找到"
new = """              rt_memcpy(p_dest_row, p_src_row, CAMERA_FRAME_LINE_BYTES);
          }

          d2_device *hdl_d2 = d2_handle_obj_get();
          if (NULL != hdl_d2)
          {
              d2_brighten_overlay(hdl_d2, p_src,
                                  CAMERA_CAPTURE_IMAGE_WIDTH, CAMERA_CAPTURE_IMAGE_HEIGHT,
                                  p_dest, DISPLAY_SCREEN_WIDTH, DISPLAY_SCREEN_HEIGHT,
                                  x_offset, 0);
          }"""
s = s.replace(old, new, 1)

open(P, "w", encoding="utf-8", errors="surrogateescape").write(s)
print("dave2d additive brightening inserted")
