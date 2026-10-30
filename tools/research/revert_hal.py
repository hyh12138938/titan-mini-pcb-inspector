import re
P = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\project\Titan_Mini_pad_inspect\src\hal_entry.c"
s = open(P, "r", encoding="utf-8", errors="surrogateescape").read()

# 把 "线程+超时" 那段整体换回直接调用
start = s.find("    /* \u5728\u72ec\u7acb\u7ebf\u7a0b\u91cc\u505a\u76f8\u673a\u521d\u59cb\u5316")
end = s.find("    g_stage = 1;")
assert start != -1 and end != -1 and end > start, (start, end)
s = s[:start] + """    fsp_status = camera_init(false);
    if (FSP_SUCCESS != fsp_status)
    {
        LOG_E("camera_init fail! err=%d", fsp_status);
        g_stage = -1;
        return;
    }
""" + s[end:]

# 去掉临时打点
for pat in ("    g_stage = 100;\n", "    g_stage = 101;\n", "    g_stage = 102;\n", "    g_stage = 103;\n"):
    s = s.replace(pat, "")
open(P, "w", encoding="utf-8", errors="surrogateescape").write(s)
print("reverted to direct camera_init")
print("g_stage=10 markers left:", s.count("g_stage = 10"))
