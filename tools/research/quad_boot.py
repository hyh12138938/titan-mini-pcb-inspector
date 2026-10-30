P = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\project\Titan_Mini_pad_inspect\src\hal_entry.c"
s = open(P, "r", encoding="utf-8", errors="surrogateescape").read()
anchor = """    /* bring-up marker: draw before camera init so a hang is visible on screen */"""
assert anchor in s
quad = """    /* QUADRANT SELF-TEST: painted by the firmware itself for 3 s at boot.
       lets us verify that what the host reads from fb_background[0] is what the panel shows. */
    scr_rect(0, 0, LCD_WIDTH / 2, LCD_HEIGHT / 2, 0xF800);                   /* top-left  red   */
    scr_rect(LCD_WIDTH / 2, 0, LCD_WIDTH / 2, LCD_HEIGHT / 2, 0x07E0);       /* top-right green */
    scr_rect(0, LCD_HEIGHT / 2, LCD_WIDTH / 2, LCD_HEIGHT / 2, 0x001F);      /* bot-left  blue  */
    scr_rect(LCD_WIDTH / 2, LCD_HEIGHT / 2, LCD_WIDTH / 2, LCD_HEIGHT / 2, 0xFFFF); /* bot-right white */
    rt_thread_mdelay(3000);

""" + anchor
s = s.replace(anchor, quad, 1)
open(P, "w", encoding="utf-8", errors="surrogateescape").write(s)
print("boot quadrant self-test added")
