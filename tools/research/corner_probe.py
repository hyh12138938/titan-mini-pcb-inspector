P = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\project\Titan_Mini_pad_inspect\src\hal_entry.c"
s = open(P, "r", encoding="utf-8", errors="surrogateescape").read()
old = """    if (fill_ok)
    {
        d2_setcolor(hdl, 0, fill_argb);
        d2_renderbox(hdl, D2_FIX(LCD_WIDTH - 90), D2_FIX(20), D2_FIX(70), D2_FIX(70));
    }"""
new = """    if (fill_ok)
    {
        /* orientation probe: one block at each diagonal corner, 100x100, opaque.
           on the 180-deg flipped panel the framebuffer top-right shows bottom-left. */
        d2_setcolor(hdl, 0, fill_argb);
        d2_renderbox(hdl, D2_FIX(LCD_WIDTH - 110), D2_FIX(10), D2_FIX(100), D2_FIX(100));
        d2_setcolor(hdl, 0, 0xFF0000FFu);
        d2_renderbox(hdl, D2_FIX(10), D2_FIX(LCD_HEIGHT - 110), D2_FIX(100), D2_FIX(100));
    }"""
assert old in s
s = s.replace(old, new, 1)
open(P, "w", encoding="utf-8", errors="surrogateescape").write(s)
print("corner probes added")
