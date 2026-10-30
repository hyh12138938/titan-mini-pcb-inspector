P = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\project\Titan_Mini_pad_inspect\src\hal_entry.c"
s = open(P, "r", encoding="utf-8", errors="surrogateescape").read()

# hal_entry 入口 + 各阶段打点
s = s.replace('''void hal_entry(void)
{
    LOG_I''', '''void hal_entry(void)
{
    g_stage = 100;
    LOG_I''', 1)
s = s.replace("    build_pix_lut();", "    g_stage = 101;\n    build_pix_lut();", 1)
s = s.replace("    cam_boot_start();", "    g_stage = 102;\n    cam_boot_start();", 1)
s = s.replace("    for (int i = 0; i < 100 && cam_boot_state == 0; i++)",
              "    g_stage = 103;\n    for (int i = 0; i < 100 && cam_boot_state == 0; i++)", 1)
open(P, "w", encoding="utf-8", errors="surrogateescape").write(s)
print("markers added")
