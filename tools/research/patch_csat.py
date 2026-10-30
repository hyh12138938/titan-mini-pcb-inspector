# -*- coding: utf-8 -*-
import io
p = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\project\Titan_Mini_driver_eth\src\cam_snap.c"
s = io.open(p, "r", encoding="utf-8").read()

# 色度强度开关
anchor = u"static int s_cnr = 1;"
s = s.replace(anchor, anchor + u"\nstatic int s_csat = 55;   /* 色彩强度 0..100：低照度时压低色度，显著减少彩色噪点 */", 1)

# 在 CNR 之后、ACC 之前插入去饱和
old = u"""            accR += (rt_uint32_t) R;
            accG += (rt_uint32_t) G;
            accB += (rt_uint32_t) B;
            npx++;"""
new = u"""            /* 色度压暗（灰世界混合）：低照度下彩色噪点最刺眼，按比例向亮度靠拢 */
            if (s_csat < 100)
            {
                int Y = (R * 299 + G * 587 + B * 114) / 1000;
                int k = 100 - s_csat;

                R = (R * s_csat + Y * k) / 100;
                G = (G * s_csat + Y * k) / 100;
                B = (B * s_csat + Y * k) / 100;
            }

            accR += (rt_uint32_t) R;
            accG += (rt_uint32_t) G;
            accB += (rt_uint32_t) B;
            npx++;"""
s = s.replace(old, new, 1)

anchor2 = u"MSH_CMD_EXPORT(cam_cnr, cam_cnr <0|1>: chroma noise reduction);"
s = s.replace(anchor2, anchor2 + u'''

/* cam_csat <0..100>：色彩强度（越小越灰，彩色噪点越少） */
static void cam_csat(int argc, char **argv)
{
    if (argc >= 2)
    {
        int v = atoi(argv[1]);
        if (v < 0)   v = 0;
        if (v > 100) v = 100;
        s_csat = v;
    }
    rt_kprintf("csat: %d\\n", s_csat);
}
MSH_CMD_EXPORT(cam_csat, cam_csat <0..100>: chroma strength);''', 1)

io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("ok")
