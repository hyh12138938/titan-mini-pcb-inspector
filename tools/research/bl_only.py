P = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\libraries\Common\ports\mipicsi_camera\camera_layer_config.h"
b = open(P, "rb").read()
old = b"#define CAMERA_CONFIG_BRIGHTNESS     (CONFIG_BRIGHTNESS_ZERO)"
new = b"#define CAMERA_CONFIG_BRIGHTNESS     (CONFIG_BRIGHTNESS_PLUS_3)"
print("found:", old in b)
open(P, "wb").write(b.replace(old, new))
