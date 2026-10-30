# -*- coding: utf-8 -*-
import io
p = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\project\Titan_Mini_driver_eth\src\cam_snap.c"
s = io.open(p, "r", encoding="utf-8").read()

anchor = u"static rt_thread_t s_stream_tid = RT_NULL;"
s = s.replace(anchor, anchor + u"\nstatic int s_auto_start = 1;   /* 开机自动推流（等网络就绪后启动） */", 1)

# 在 cam_stream 命令之前插入 helper + 自启线程
anchor2 = u"static void cam_stream(int argc, char **argv)"
helper = u'''/* 启动推流（命令与开机自启共用） */
static int cam_stream_begin(void)
{
    if (s_stream_run)
    {
        return 0;
    }
    if (cam_ensure_ready() != 0)
    {
        return -1;
    }

    s_stream_run = 1;
    s_stream_tid = rt_thread_create("cam_strm", cam_stream_thread, RT_NULL,
                                    CAM_STREAM_STACK, 15, 10);
    if (s_stream_tid == RT_NULL)
    {
        s_stream_run = 0;
        rt_kprintf("[cam] create thread failed\\n");
        return -1;
    }
    rt_thread_startup(s_stream_tid);
    return 0;
}

/* 开机自启：等 DHCP 拿到 IP 后再推流 */
static void cam_auto_thread(void *arg)
{
    rt_thread_mdelay(8000);

    if (s_auto_start && !s_stream_run)
    {
        rt_kprintf("[cam] auto stream start -> %s (%d fps, div=%d)\\n",
                   s_stream_url, s_stream_fps, s_stream_div);
        cam_stream_begin();
    }
}

static int cam_auto_init(void)
{
    rt_thread_t t = rt_thread_create("cam_auto", cam_auto_thread, RT_NULL, 2048, 20, 10);

    if (t != RT_NULL)
    {
        rt_thread_startup(t);
    }
    return 0;
}
INIT_ENV_EXPORT(cam_auto_init);

static void cam_auto(int argc, char **argv)
{
    if (argc >= 2)
    {
        s_auto_start = (atoi(argv[1]) != 0) ? 1 : 0;
    }
    rt_kprintf("auto start: %s\\n", s_auto_start ? "on" : "off");
}
MSH_CMD_EXPORT(cam_auto, cam_auto <0|1>: auto stream on boot);

'''
s = s.replace(anchor2, helper + anchor2, 1)

io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("ok")
