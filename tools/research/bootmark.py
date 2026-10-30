P = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\project\Titan_Mini_pad_inspect\src\hal_entry.c"
s = open(P, "r", encoding="utf-8", errors="surrogateescape").read()
old = "    build_pix_lut();\n\n    fsp_status = camera_init(false);"
new = """    /* bring-up marker: draw before camera init so a hang is visible on screen */
    scr_fill(0x0320);                                    /* dark green */
    scr_rect(0, 0, LCD_WIDTH, 36, 0xF800);               /* red bar on top */
    scr_rect(0, LCD_HEIGHT - 36, LCD_WIDTH, 36, 0x001F); /* blue bar at bottom */

    build_pix_lut();

    fsp_status = camera_init(false);"""
assert old in s
s = s.replace(old, new, 1)
open(P, "w", encoding="utf-8", errors="surrogateescape").write(s)
print("boot marker added")
