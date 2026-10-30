# 1) 回退手动曝光，恢复视频流
P = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\libraries\Common\ports\mipicsi_camera\camera_layer.c"
b = open(P,"rb").read()
lines = b.split(b"\r\n")
out = [l for l in lines if not (b"0x3503, 0x03" in l or b"0x3500, 0x00" in l or b"0x3508, 0x02" in l)]
b2 = b"\r\n".join(out)
open(P,"wb").write(b2)
print("manual exposure removed:", b"0x3503, 0x03" not in b2)

# 2) 显示侧增益
H = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\project\Titan_Mini_pad_inspect\src\hal_entry.c"
s = open(H, "r", encoding="utf-8", errors="surrogateescape").read()

fn = '''
/* \u663e\u793a\u4fa7\u589e\u76ca\uff08\u4e0d\u5f71\u54cd\u6a21\u578b\u8f93\u5165\uff09\uff1a\u628a\u955c\u5934\u753b\u9762\u63d0\u4eae\u540e\u518d\u9001\u5c4f */
#define DISP_GAIN16   32          /* 16 = 1.0x, 32 = 2.0x, 40 = 2.5x */
static void frame_brighten(uint16_t *fb)
{
    uint32_t n = (uint32_t)CAM_WIDTH * CAM_HEIGHT;
    for (uint32_t i = 0; i < n; i++)
    {
        uint16_t c = fb[i];
        int32_t r = (c >> 11) & 0x1F;
        int32_t g = (c >> 5) & 0x3F;
        int32_t b = c & 0x1F;
        r = (r * DISP_GAIN16) >> 4; if (r > 31) r = 31;
        g = (g * DISP_GAIN16) >> 4; if (g > 63) g = 63;
        b = (b * DISP_GAIN16) >> 4; if (b > 31) b = 31;
        fb[i] = (uint16_t)((r << 11) | (g << 5) | b);
    }
}
'''
s = s.replace("static void build_pix_lut(void)", fn + "\nstatic void build_pix_lut(void)", 1)
s = s.replace("        frame_to_input(frame);", "        frame_to_input(frame);\n        frame_brighten(frame);", 1)
open(H, "w", encoding="utf-8", errors="surrogateescape").write(s)
print("display gain added")
