import pymupdf, os
p = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\docs\Titan_Mini_schematic_v1.0.pdf"
doc = pymupdf.open(p)
out = r"D:\RTT\_re\sch"
os.makedirs(out, exist_ok=True)
for i in (2, 5, 12):          # 0-based: p03, p06, p13
    pg = doc[i]
    r = pg.rect
    print(f"p{i+1}: {r.width:.0f}x{r.height:.0f} pt")
    pix = pg.get_pixmap(matrix=pymupdf.Matrix(3, 3))
    f = os.path.join(out, f"p{i+1:02d}.png")
    pix.save(f)
    print("  ->", f, f"{pix.width}x{pix.height}", f"{os.path.getsize(f)/1024:.0f} KB")
