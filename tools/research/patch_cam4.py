P = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\project\Titan_Mini_pad_inspect\src\hal_entry.c"
s = open(P, "r", encoding="utf-8", errors="surrogateescape").read()

old_decl = "extern uint16_t fb_background[];"
new_decl = ("extern uint8_t fb_background[][DISPLAY_BUFFER_STRIDE_BYTES_INPUT0 * DISPLAY_VSIZE_INPUT0];\n"
            "#define FB16 ((uint16_t *)fb_background[0])")
assert old_decl in s
s = s.replace(old_decl, new_decl, 1)

s = s.replace("        fb_background[i] = color;", "        FB16[i] = color;")
s = s.replace("            fb_background[j * LCD_WIDTH + i] = color;", "            FB16[j * LCD_WIDTH + i] = color;")
open(P, "w", encoding="utf-8", errors="surrogateescape").write(s)
print("fixed fb type")
