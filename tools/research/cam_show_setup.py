# -*- coding: utf-8 -*-
"""在干净的官方摄像头示例副本上，只加「显示侧亮度 + 白平衡」，其余一律不动。"""
import re

P = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\project\Titan_Mini_cam_show\src\hal_entry.c"
s = open(P, "r", encoding="utf-8", errors="surrogateescape").read()

# ---------- 1) 插入 64K 查表（亮度 + 白平衡） ----------
lut = r'''
/* ------------------------------------------------------------------
 *  display-side tone mapping only (nothing else is touched):
 *  out = clamp((in - black) * gain) per channel, white balance folded in.
 *  precomputed as a 65536-entry RGB565 -> RGB565 table, one lookup/pixel.
 * ------------------------------------------------------------------ */
#define BLACK_R    2           /* of 31 */
#define BLACK_G    6           /* of 63 */
#define BLACK_B    2           /* of 31 */
#define GAIN_R16   36          /* 2.25x, includes red WB   */
#define GAIN_G16   31          /* 1.94x                    */
#define GAIN_B16   32          /* 2.00x, includes blue WB  */

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
anchor = "void DisplayVsyncCallback(display_callback_args_t * p_args)"
assert anchor in s
s = s.replace(anchor, lut + anchor, 1)

# ---------- 2) 拷贝循环改成查表（同时把画面居中：x_offset 用居中值） ----------
old_loop = """          int x_offset = DISPLAY_SCREEN_WIDTH - CAMERA_CAPTURE_IMAGE_WIDTH;

          for (int y = 0; y < CAMERA_CAPTURE_IMAGE_HEIGHT; y++)
          {
              uint16_t * p_dest_row = p_dest + (y * DISPLAY_SCREEN_WIDTH) + x_offset;
              uint16_t * p_src_row  = p_src + (y * CAMERA_CAPTURE_IMAGE_WIDTH);

              rt_memcpy(p_dest_row, p_src_row, CAMERA_FRAME_LINE_BYTES);
          }"""
new_loop = """          /* centred 1:1 placement (no scaling -> no moire stripes) */
          int x_offset = (DISPLAY_SCREEN_WIDTH - CAMERA_CAPTURE_IMAGE_WIDTH) / 2;

          for (int y = 0; y < CAMERA_CAPTURE_IMAGE_HEIGHT; y++)
          {
              uint16_t * p_dest_row = p_dest + (y * DISPLAY_SCREEN_WIDTH) + x_offset;
              uint16_t * p_src_row  = p_src + (y * CAMERA_CAPTURE_IMAGE_WIDTH);

              for (int x = 0; x < CAMERA_CAPTURE_IMAGE_WIDTH; x++)
              {
                  p_dest_row[x] = g_tone_lut[p_src_row[x]];
              }
          }"""
assert old_loop in s
s = s.replace(old_loop, new_loop, 1)

# ---------- 3) 启动时建表 ----------
old_start = """      rt_kprintf ("\\nHello Titan Board!\\n");"""
new_start = """      tone_lut_build();

      rt_kprintf ("\\nHello Titan Board!\\n");"""
assert old_start in s
s = s.replace(old_start, new_start, 1)

open(P, "w", encoding="utf-8", errors="surrogateescape").write(s)
print("clean base + tone mapping applied")
print("  has lut:", "g_tone_lut" in s)
print("  has centering:", "centred 1:1" in s)
