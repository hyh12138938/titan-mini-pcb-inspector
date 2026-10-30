P = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\project\Titan_Mini_pad_inspect\src\hal_entry.c"
s = open(P, "r", encoding="utf-8", errors="surrogateescape").read()

# 1) 1:1 居中 blit（消除 1.25x 缩放摩尔纹）
old_blit = """    d2_blitcopy(hdl, xSize, ySize, 0, 0,
                D2_FIX(LCD_WIDTH), D2_FIX(LCD_HEIGHT),
                D2_FIX(0), D2_FIX(0), 0);"""
new_blit = """    /* 1:1 \u5c45\u4e2d\uff0c\u4e0d\u505a 640->800 \u7f29\u653e\uff08\u5426\u5219\u4f1a\u51fa\u73b0 5px \u5468\u671f\u7684\u7eb5\u5411\u6478\u5c14\u7eb9\uff09 */
    d2_blitcopy(hdl, xSize, ySize, 0, 0,
                D2_FIX(xSize), D2_FIX(ySize),
                D2_FIX(FB_XOFF), D2_FIX(FB_YOFF), 0);"""
assert old_blit in s
s = s.replace(old_blit, new_blit, 1)

# 2) 增加偏移宏
s = s.replace("#define CAM_WIDTH   640", "#define CAM_WIDTH   640\n#define FB_XOFF     ((LCD_WIDTH - CAM_WIDTH) / 2)   /* 80 */\n#define FB_YOFF     ((LCD_HEIGHT - CAM_HEIGHT) / 2) /* 0 */", 1)

# 3) 送屏前先把两边空白填黑，避免残留
s = s.replace("    d2_setblitsrc(hdl, (void *)p, xSize, xSize, ySize, ModeSrc);",
              "    d2_setcolor(hdl, 0, 0xFF000000u);\n    d2_renderbox(hdl, D2_FIX(0), D2_FIX(0), D2_FIX(LCD_WIDTH), D2_FIX(LCD_HEIGHT));\n    d2_setblitsrc(hdl, (void *)p, xSize, xSize, ySize, ModeSrc);", 1)

# 4) ROI 框坐标加上偏移
s = s.replace("""        box.x1 = (roi_cx - half) * LCD_WIDTH  / CAM_WIDTH;
        box.y1 = (roi_cy - half) * LCD_HEIGHT / CAM_HEIGHT;
        box.x2 = (roi_cx + half) * LCD_WIDTH  / CAM_WIDTH;
        box.y2 = (roi_cy + half) * LCD_HEIGHT / CAM_HEIGHT;""",
"""        box.x1 = FB_XOFF + (roi_cx - half);
        box.y1 = FB_YOFF + (roi_cy - half);
        box.x2 = FB_XOFF + (roi_cx + half);
        box.y2 = FB_YOFF + (roi_cy + half);""", 1)

open(P, "w", encoding="utf-8", errors="surrogateescape").write(s)
print("1:1 blit + offsets applied")
