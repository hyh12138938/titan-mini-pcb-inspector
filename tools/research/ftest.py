P = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\project\Titan_Mini_pad_inspect\src\hal_entry.c"
s = open(P, "r", encoding="utf-8", errors="surrogateescape").read()

a = s.find("    /* DAVE2D SELF TEST")
b = s.find("    /* bring-up marker:")
assert a != -1 and b > a

ftest = '''    /* ORIENTATION TEST: draw a big letter "F" plus a red corner marker, hold 6 s.
       "F" is asymmetric, so the photo tells us exactly whether the panel is
       rotated 0/90/180/270 or mirrored. Drawn straight into the framebuffer. */
    scr_fill(0x0000);
    scr_rect(100,  80,  70, 320, 0xFFFF);   /* F: vertical stroke */
    scr_rect(170,  80, 240,  70, 0xFFFF);   /* F: top bar        */
    scr_rect(170, 200, 160,  70, 0xFFFF);   /* F: middle bar     */
    scr_rect(LCD_WIDTH - 90, 20, 70, 70, 0xF800);  /* red marker at fb top-right */
    scr_rect(20, LCD_HEIGHT - 90, 70, 70, 0x07E0); /* green marker at fb bottom-left */
    rt_thread_mdelay(6000);

'''
s = s[:a] + ftest + s[b:]
open(P, "w", encoding="utf-8", errors="surrogateescape").write(s)
print("F orientation test added")
