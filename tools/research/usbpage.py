import pymupdf
p = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\docs\Titan_Mini_schematic_v1.0.pdf"
doc = pymupdf.open(p)
for i in (0, 4, 12):   # p01, p05, p13
    t = doc[i].get_text().splitlines()
    print(f"\n===== p{i+1:02d} ({len(t)} lines) =====")
    for ln in t[:45]:
        ln = ln.strip()
        if ln: print("  ", ln[:100])
