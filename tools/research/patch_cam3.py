P = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\project\Titan_Mini_pad_inspect\src\hal_entry.c"
s = open(P, "r", encoding="utf-8", errors="surrogateescape").read()

impl = '''
/* ---- \u76f8\u673a\u521d\u59cb\u5316\u7ebf\u7a0b ---- */
volatile int cam_boot_state;   /* 0=\u8fdb\u884c\u4e2d 1=\u6210\u529f -1=\u5931\u8d25 */

static void cam_boot_thread(void *arg)
{
    (void)arg;
    fsp_err_t st = camera_init(false);
    cam_boot_state = (FSP_SUCCESS == st) ? 1 : -1;
}

rt_err_t cam_boot_start(void)
{
    rt_thread_t th = rt_thread_create("camb", cam_boot_thread, RT_NULL, 8192, 12, 10);
    if (th == RT_NULL)
    {
        return -RT_ERROR;
    }
    rt_thread_startup(th);
    return RT_EOK;
}
'''
anchor = "static void build_pix_lut(void)"
assert anchor in s
s = s.replace(anchor, impl + "\n" + anchor, 1)
open(P, "w", encoding="utf-8", errors="surrogateescape").write(s)
print("impl added")
