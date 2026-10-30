P = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\project\Titan_Mini_cam_bright\src\hal_entry.c"
lines = open(P, "r", encoding="utf-8", errors="surrogateescape").readlines()
start = next(i for i,l in enumerate(lines) if l.startswith("static void tone_lut_build(void)"))
end   = next(i for i,l in enumerate(lines) if l.startswith("void DisplayVsyncCallback"))
del lines[start:end]
open(P, "w", encoding="utf-8", errors="surrogateescape").writelines(lines)
print("deleted orphan tone_lut_build:", start+1, "..", end)
