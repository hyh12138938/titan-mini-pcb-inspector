# -*- coding: utf-8 -*-
import io
p = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\project\Titan_Mini_driver_eth\src\cam_snap.c"
s = io.open(p, "r", encoding="utf-8").read()

# 1) 新增开关与行缓冲
anchor = u"/* 推给 PC 的像素格式：1=RGB888（默认，避免 5bit 量化放大出彩色噪点），0=RGB565 */\nstatic int s_fmt888 = 1;"
add = anchor + u'''

/* 彩色噪点抑制：只平滑色度(R/B)，保留亮度(G)细节，3 抽头可分离滤波 */
static int s_cnr = 1;
static unsigned char s_prevR[320], s_prevB[320];'''
s = s.replace(anchor, add, 1)

# 2) 在每行开始前重置上一行缓存标记
s = s.replace(u"""    for (y = 0; y < h; y++)
    {
        unsigned char *dst = s_push_buf + y * w * bpp;""",
u"""    lastR = lastB = 0;

    for (y = 0; y < h; y++)
    {
        unsigned char *dst = s_push_buf + y * w * bpp;""", 1)

# 3) 声明 lastR/lastB
s = s.replace(u"    int w, h, x, y, bpp, len;\n    rt_uint32_t accR = 0, accG = 0, accB = 0, npx = 0;",
              u"    int w, h, x, y, bpp, len;\n    int lastR = 0, lastB = 0;\n    rt_uint32_t accR = 0, accG = 0, accB = 0, npx = 0;", 1)

# 4) 平滑插入点：ACC 累加之前
old = u"""            accR += (rt_uint32_t) R;
            accG += (rt_uint32_t) G;
            accB += (rt_uint32_t) B;
            npx++;"""
new = u"""            /* 色度噪声抑制：R/B 做 3 抽头平滑（左 + 上），G 保持不动 */
            if (s_cnr && w <= 320)
            {
                int R2 = R, B2 = B;

                if (x > 0)
                {
                    R2 = (R * 2 + lastR) / 3;
                    B2 = (B * 2 + lastB) / 3;
                }
                if (y > 0)
                {
                    R2 = (R2 * 2 + s_prevR[x]) / 3;
                    B2 = (B2 * 2 + s_prevB[x]) / 3;
                }
                lastR = R; lastB = B;
                s_prevR[x] = (unsigned char) R;
                s_prevB[x] = (unsigned char) B;
                R = R2; B = B2;
            }

            accR += (rt_uint32_t) R;
            accG += (rt_uint32_t) G;
            accB += (rt_uint32_t) B;
            npx++;"""
s = s.replace(old, new, 1)

# 5) 命令
anchor2 = u"MSH_CMD_EXPORT(cam_fmt, cam_fmt 888|565: pixel format pushed to PC);"
s = s.replace(anchor2, anchor2 + u'''

/* cam_cnr <0|1>：彩色噪点抑制开关 */
static void cam_cnr(int argc, char **argv)
{
    if (argc >= 2)
    {
        s_cnr = (atoi(argv[1]) != 0) ? 1 : 0;
    }
    rt_kprintf("cnr: %s\\n", s_cnr ? "on" : "off");
}
MSH_CMD_EXPORT(cam_cnr, cam_cnr <0|1>: chroma noise reduction);''', 1)

io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("ok")
