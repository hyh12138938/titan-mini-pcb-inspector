P = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\project\Titan_Mini_pad_inspect\src\hal_entry.c"
s = open(P, "r", encoding="utf-8", errors="surrogateescape").read()
anchor = "    d2_cliprect(hdl, 0, 0, LCD_WIDTH, LCD_HEIGHT);"
assert anchor in s
rot = """    d2_cliprect(hdl, 0, 0, LCD_WIDTH, LCD_HEIGHT);

    /* the panel is mounted 180 deg rotated w.r.t. the framebuffer (verified with a
       four-quadrant self test), so rotate all drawing by 180 deg here:
       x' = W - x, y' = H - y  (16.16 fixed point) */
    d2_setmatrix(hdl, -(1 << 16), 0, 0, -(1 << 16), (LCD_WIDTH << 16), (LCD_HEIGHT << 16));"""
s = s.replace(anchor, rot, 1)
open(P, "w", encoding="utf-8", errors="surrogateescape").write(s)
print("180-degree rotation applied")
