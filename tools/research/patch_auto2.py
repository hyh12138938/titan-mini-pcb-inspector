# -*- coding: utf-8 -*-
import io
p = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\project\Titan_Mini_driver_eth\src\cam_snap.c"
s = io.open(p, "r", encoding="utf-8").read()

# 1) 自启线程：延后到 15s，并带重试
old_auto = u'''static void cam_auto_thread(void *arg)
{
    rt_thread_mdelay(8000);

    if (s_auto_start && !s_stream_run)
    {
        rt_kprintf("[cam] auto stream start -> %s (%d fps, div=%d)\\n",
                   s_stream_url, s_stream_fps, s_stream_div);
        cam_stream_begin();
    }
}'''
new_auto = u'''static void cam_auto_thread(void *arg)
{
    int i;

    /* 等网络与各驱动彻底稳定（早期初始化会让 VIN 抓不到帧） */
    rt_thread_mdelay(15000);

    for (i = 0; i < 12; i++)
    {
        if (!s_auto_start || s_stream_run)
        {
            return;
        }
        if (cam_stream_begin() == 0)
        {
            rt_kprintf("[cam] auto stream ok -> %s (%d fps, div=%d)\\n",
                       s_stream_url, s_stream_fps, s_stream_div);
            return;
        }
        rt_kprintf("[cam] auto stream retry %d\\n", i + 1);
        rt_thread_mdelay(5000);
    }
}'''
s = s.replace(old_auto, new_auto, 1)

# 2) 推流线程：连续失败后自动重初始化相机
old_thr = u'''        if (cam_push_once(s_stream_url, s_stream_div, 1) == 0)
        {
            ok++;
        }
        else
        {
            fail++;
        }'''
new_thr = u'''        if (cam_push_once(s_stream_url, s_stream_div, 1) == 0)
        {
            ok++;
        }
        else
        {
            fail++;

            /* 连续拿不到帧：重建相机（VIN 偶尔会在早期初始化后停摆） */
            if ((fail % 20) == 0)
            {
                rt_kprintf("[cam] stream stuck (fail=%d), reinit camera\\n", fail);
                s_cam_ready = 0;
                cam_ensure_ready();
            }
        }'''
s = s.replace(old_thr, new_thr, 1)

# 3) cam_reinit 命令
anchor = u"MSH_CMD_EXPORT(cam_auto, cam_auto <0|1>: auto stream on boot);"
s = s.replace(anchor, anchor + u'''

/* cam_reinit：重建相机（VIN/传感器），推流停摆时用 */
static void cam_reinit(int argc, char **argv)
{
    (void) argc; (void) argv;

    rt_kprintf("[cam] reinit...\\n");
    s_cam_ready = 0;
    rt_kprintf("[cam] %s\\n", (cam_ensure_ready() == 0) ? "ok" : "failed");
}
MSH_CMD_EXPORT(cam_reinit, cam_reinit: reinitialize camera);''', 1)

io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("ok")
