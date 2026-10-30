# -*- coding: utf-8 -*-
import io, re, sys
p = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\project\Titan_Mini_driver_eth\src\cam_snap.c"
src = io.open(p, "r", encoding="utf-8").read()

new_pack = u'''/* 把一帧降采样进 s_push_buf，返回字节数（0 = 失败）
 * 关键：增益在 8bit 域完成，再按 s_fmt888 输出 —— 避免在 5bit 量化格上放大出彩色噪点 */
static int cam_pack(int div, int *pw, int *ph)
{
    uint16_t *fb;
    int w, h, x, y, bpp, len;
    rt_uint32_t accR = 0, accG = 0, accB = 0, npx = 0;

    if (div < 1) div = 1;
    if (div > 4) div = 4;

    w = CAMERA_CAPTURE_IMAGE_WIDTH / div;
    h = CAMERA_CAPTURE_IMAGE_HEIGHT / div;
    bpp = s_fmt888 ? 3 : 2;
    len = w * h * bpp;

    if (len > (int) sizeof(s_push_buf))
    {
        rt_kprintf("[cam] frame too big (%d B)\\n", len);
        return 0;
    }

    fb = cam_wait_frame(3000);
    if (fb == RT_NULL)
    {
        return 0;
    }

    for (y = 0; y < h; y++)
    {
        unsigned char *dst = s_push_buf + y * w * bpp;

        for (x = 0; x < w; x++)
        {
            int rs = 0, gs = 0, bs = 0, cnt = 0, dy, dx;
            int r5, g6, b5, R, G, B;

            /* div x div box average */
            for (dy = 0; dy < div; dy++)
            {
                uint16_t *row = fb + (y * div + dy) * CAMERA_CAPTURE_IMAGE_WIDTH + x * div;

                for (dx = 0; dx < div; dx++)
                {
                    uint16_t px = row[dx];
                    rs += (px >> 11) & 0x1F;
                    gs += (px >> 5) & 0x3F;
                    bs += px & 0x1F;
                    cnt++;
                }
            }
            if (cnt == 0) cnt = 1;

            r5 = rs / cnt;
            g6 = gs / cnt;
            b5 = bs / cnt;

            R = (r5 << 3) | (r5 >> 2);
            G = (g6 << 2) | (g6 >> 4);
            B = (b5 << 3) | (b5 >> 2);

            if (s_gain > 1)
            {
                R *= s_gain; if (R > 255) R = 255;
                G *= s_gain; if (G > 255) G = 255;
                B *= s_gain; if (B > 255) B = 255;
            }

            R = (R * s_gR) >> 8; if (R > 255) R = 255;
            G = (G * s_gG) >> 8; if (G > 255) G = 255;
            B = (B * s_gB) >> 8; if (B > 255) B = 255;

            accR += (rt_uint32_t) R;
            accG += (rt_uint32_t) G;
            accB += (rt_uint32_t) B;
            npx++;

            if (s_fmt888)
            {
                dst[3 * x]     = (unsigned char) R;
                dst[3 * x + 1] = (unsigned char) G;
                dst[3 * x + 2] = (unsigned char) B;
            }
            else
            {
                uint16_t out = (uint16_t) (((R >> 3) << 11) | ((G >> 2) << 5) | (B >> 3));
                dst[2 * x]     = (unsigned char) (out & 0xFF);
                dst[2 * x + 1] = (unsigned char) ((out >> 8) & 0xFF);
            }
        }
    }

    /* 用本帧结果修正下一帧通道增益：R/G/B 均值同时趋向目标亮度（自动曝光 + 灰世界白平衡） */
    if (s_agc && npx)
    {
        int mR = (int) (accR / npx);
        int mG = (int) (accG / npx);
        int mB = (int) (accB / npx);
        int t  = s_target_luma;

        if (mR < 2) mR = 2;
        if (mG < 2) mG = 2;
        if (mB < 2) mB = 2;

        s_gR = (s_gR * t) / mR;
        s_gG = (s_gG * t) / mG;
        s_gB = (s_gB * t) / mB;

        if (s_gR < 128)  s_gR = 128;
        if (s_gR > 4096) s_gR = 4096;
        if (s_gG < 128)  s_gG = 128;
        if (s_gG > 4096) s_gG = 4096;
        if (s_gB < 128)  s_gB = 128;
        if (s_gB > 4096) s_gB = 4096;
    }

    if (pw) *pw = w;
    if (ph) *ph = h;
    return len;
}
'''

start = src.index(u"/* 把一帧降采样进 s_push_buf")
end   = src.index(u"    return w * h * 2;\n}", start) + len(u"    return w * h * 2;\n}")
src = src[:start] + new_pack + src[end:]

# cam_post: 格式头
src = src.replace(u'webclient_header_fields_add(s, "X-Format: rgb565\\r\\n");',
                  u'webclient_header_fields_add(s, "X-Format: %s\\r\\n", s_fmt888 ? "rgb888" : "rgb565");')

# cam_luma: 支持 888
old_luma_start = src.index(u"static int cam_luma(int len)")
old_luma_end   = src.index(u"\n}\n", old_luma_start) + 3
new_luma = u'''static int cam_luma(int len)
{
    rt_uint32_t acc = 0;
    int i, n;

    if (s_fmt888)
    {
        n = len / 3;
        for (i = 0; i < n; i++)
        {
            acc += (rt_uint32_t) ((s_push_buf[3 * i + 0] * 299 +
                                   s_push_buf[3 * i + 1] * 587 +
                                   s_push_buf[3 * i + 2] * 114) / 1000);
        }
    }
    else
    {
        n = len / 2;
        for (i = 0; i < n; i++)
        {
            uint16_t v = (uint16_t) (s_push_buf[2 * i] | (s_push_buf[2 * i + 1] << 8));
            acc += (rt_uint32_t) (((v >> 11) & 0x1F) * 8 * 299 +
                                  ((v >> 5) & 0x3F) * 4 * 587 +
                                  (v & 0x1F) * 8 * 114) / 1000;
        }
    }
    return (n > 0) ? (int) (acc / n) : 0;
}
'''
src = src[:old_luma_start] + new_luma + src[old_luma_end:]

# 新增 cam_fmt 命令（挂在 cam_agc 导出之后）
anchor = u'MSH_CMD_EXPORT(cam_agc, cam_agc <0|1> [target]: auto brightness and white balance);'
cmd = anchor + u'''

/* 输出格式：cam_fmt 888|565 （888 默认，彩色噪点明显更少） */
static void cam_fmt(int argc, char **argv)
{
    if (argc >= 2)
    {
        s_fmt888 = (atoi(argv[1]) == 565) ? 0 : 1;
    }
    rt_kprintf("format: %s\\n", s_fmt888 ? "rgb888" : "rgb565");
}
MSH_CMD_EXPORT(cam_fmt, cam_fmt 888|565: pixel format pushed to PC);'''
src = src.replace(anchor, cmd)

io.open(p, "w", encoding="utf-8", newline="\n").write(src)
print("patched ok")
