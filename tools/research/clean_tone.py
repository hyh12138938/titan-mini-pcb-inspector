P = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\project\Titan_Mini_cam_bright\src\hal_entry.c"
lines = open(P, "r", encoding="utf-8", errors="surrogateescape").readlines()
start = next((i for i,l in enumerate(lines) if "display-side brightening only" in l), None)
if start is None:
    start = next((i for i,l in enumerate(lines) if l.startswith("/* ---")), None)
end = next((i for i,l in enumerate(lines) if l.startswith("void DisplayVsyncCallback")), None)
print("  start/end:", start, end)
if start is not None and end is not None and end > start:
    del lines[start:end]
    open(P, "w", encoding="utf-8", errors="surrogateescape").writelines(lines)
    print("  removed lines", start+1, "..", end)
else:
    print("  nothing removed")
