files = [
 r"D:\RTT\sdk-bsp-ra8p1-titan-mini\project\Titan_Mini_cam_bright\ra_cfg\fsp_cfg\r_glcdc_cfg.h",
 r"D:\RTT\sdk-bsp-ra8p1-titan-mini\project\Titan_Mini_cam_bright\ra_gen\common_data.h",
 r"D:\RTT\sdk-bsp-ra8p1-titan-mini\FSPConfiguration\ra_cfg\fsp_cfg\r_glcdc_cfg.h",
 r"D:\RTT\sdk-bsp-ra8p1-titan-mini\FSPConfiguration\ra_gen\common_data.h",
]
for f in files:
    s = open(f, "r", encoding="utf-8", errors="surrogateescape").read()
    s = s.replace("#define GLCDC_CFG_COLOR_CORRECTION_ENABLE (true)",
                  "#define GLCDC_CFG_COLOR_CORRECTION_ENABLE (1)")
    for ch in "RGB":
        s = s.replace(f"GLCDC_CFG_CORRECTION_GAMMA_ENABLE_{ch}       (true)",
                      f"GLCDC_CFG_CORRECTION_GAMMA_ENABLE_{ch}       (1)")
        s = s.replace(f"GLCDC_CFG_CORRECTION_GAMMA_ENABLE_{ch}      (true)",
                      f"GLCDC_CFG_CORRECTION_GAMMA_ENABLE_{ch}      (1)")
    open(f, "w", encoding="utf-8", errors="surrogateescape").write(s)
    print("  updated", f.split("titan-mini")[-1])
