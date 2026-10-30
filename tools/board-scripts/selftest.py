P = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\project\Titan_Mini_pad_inspect\src\hal_entry.c"
s = open(P, "r", encoding="utf-8", errors="surrogateescape").read()

# 1) 四色块自检 -> DAVE2D 自检（不依赖摄像头）
a = s.find("    /* QUADRANT SELF-TEST")
b = s.find("    /* bring-up marker:")
assert a != -1 and b > a
selftest = '''    /* DAVE2D SELF TEST (runs before the camera, so it works even if camera_init fails):
       black image + grey status block + white ROI box, drawn exactly like the real frame. */
    for (uint32_t i = 0; i < (uint32_t)CAM_WIDTH * CAM_HEIGHT; i++) { g_rot[i] = 0x0000; }
    {
        pad_box_t tbox;
        tbox.x1 = LCD_WIDTH / 2 - 120; tbox.y1 = LCD_HEIGHT / 2 - 120;
        tbox.x2 = LCD_WIDTH / 2 + 120; tbox.y2 = LCD_HEIGHT / 2 + 120;
        lcd_draw_frame_with_boxes(g_rot, CAM_WIDTH, CAM_HEIGHT,
                                  0xFFE0E0E0u, 4, &tbox, 1, 1, 0xFF808080u);
    }
    rt_thread_mdelay(3000);

'''
s = s[:a] + selftest + s[b:]

# 2) camera_init 重试 + 失败红屏
old_cam = """    fsp_status = camera_init(false);
    if (FSP_SUCCESS != fsp_status)
    {
        LOG_E("camera_init fail! err=%d", fsp_status);
        g_stage = -1;
        return;
    }"""
new_cam = """    fsp_status = FSP_ERR_ASSERTION;
    for (int cam_try = 0; cam_try < 3; cam_try++)
    {
        fsp_status = camera_init(false);
        if (FSP_SUCCESS == fsp_status) { break; }
        LOG_E("camera_init fail (try %d) err=%d", cam_try + 1, fsp_status);
        rt_thread_mdelay(300);
    }
    if (FSP_SUCCESS != fsp_status)
    {
        LOG_E("camera_init gave up, err=%d", fsp_status);
        /* unmistakable red screen with black corner blocks: camera never came up */
        scr_fill(0xF800);
        scr_rect(0, 0, 120, 120, 0x0000);
        scr_rect(LCD_WIDTH - 120, 0, 120, 120, 0x0000);
        scr_rect(0, LCD_HEIGHT - 120, 120, 120, 0x0000);
        scr_rect(LCD_WIDTH - 120, LCD_HEIGHT - 120, 120, 120, 0x0000);
        g_stage = -1;
        return;
    }"""
assert old_cam in s
s = s.replace(old_cam, new_cam, 1)

open(P, "w", encoding="utf-8", errors="surrogateescape").write(s)
print("selftest + camera retry applied")
