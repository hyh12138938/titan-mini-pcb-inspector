import re
P = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\project\Titan_Mini_pad_inspect\src\hal_entry.c"
src = open(P, "r", encoding="utf-8", errors="surrogateescape").read()

# 1) 增加错误界面绘制工具
helper = '''
/* ---- \u65e0\u76f8\u673a\u515c\u5e95\uff1a\u76f4\u63a5\u5f80\u5e27\u7f13\u51b2\u586b\u8272\uff08GLCDC \u6301\u7eed\u626b\u63cf\uff0c\u65e0\u9700 flush\uff09 ---- */
extern uint16_t fb_background[];

static void scr_fill(uint16_t color)
{
    for (uint32_t i = 0; i < (uint32_t)LCD_WIDTH * LCD_HEIGHT; i++)
    {
        fb_background[i] = color;
    }
}

static void scr_rect(int32_t x, int32_t y, int32_t w, int32_t h, uint16_t color)
{
    for (int32_t j = y; j < y + h; j++)
    {
        if (j < 0 || j >= LCD_HEIGHT) continue;
        for (int32_t i = x; i < x + w; i++)
        {
            if (i < 0 || i >= LCD_WIDTH) continue;
            fb_background[j * LCD_WIDTH + i] = color;
        }
    }
}
'''
src = src.replace("static void build_pix_lut(void)", helper + "\nstatic void build_pix_lut(void)")

# 2) 摄像头初始化改为线程 + 超时
old = '''    fsp_status = camera_init(false);
    if (FSP_SUCCESS != fsp_status)
    {
        LOG_E("camera_init fail! err=%d", fsp_status);
        g_stage = -1;
        return;
    }
    g_stage = 1;'''
new = '''    /* \u5728\u72ec\u7acb\u7ebf\u7a0b\u91cc\u505a\u76f8\u673a\u521d\u59cb\u5316\uff0c\u5e76\u9650\u65f6\u7b49\u5f85\uff1a\u76f8\u673a\u4e0d\u5728\u4e5f\u80fd\u753b\u51fa\u9519\u8bef\u754c\u9762 */
    extern rt_err_t cam_boot_start(void);
    extern volatile int cam_boot_state;   /* 0=\u8fdb\u884c\u4e2d 1=\u6210\u529f -1=\u5931\u8d25 */
    cam_boot_start();
    for (int i = 0; i < 100 && cam_boot_state == 0; i++)
    {
        rt_thread_mdelay(50);
    }
    if (cam_boot_state != 1)
    {
        LOG_E("camera not ready (state=%d)", cam_boot_state);
        g_stage = -1;
        scr_fill(0x0841);                                  /* \u6df1\u84dd\u5e95 */
        scr_rect(20, LCD_HEIGHT - 90, 70, 70, 0xF800);     /* \u5de6\u4e0b\u7ea2\u5757 = \u65e0\u76f8\u673a */
        scr_rect(LCD_WIDTH / 2 - 100, LCD_HEIGHT / 2 - 100, 200, 200, 0x8410);
        rt_kprintf("[pad] NO CAMERA\\n");
        while (1)
        {
            rt_thread_mdelay(500);
        }
    }
    g_stage = 1;'''
assert old in src, "camera_init block not found"
src = src.replace(old, new)
open(P, "w", encoding="utf-8", errors="surrogateescape").write(src)
print("hal_entry patched")
