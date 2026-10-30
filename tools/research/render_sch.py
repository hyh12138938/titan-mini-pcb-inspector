import fitz
p = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\docs\Titan_Mini_schematic_v1.0.pdf"
doc = fitz.open(p)
out = r"D:\RTT\_re\titan_docs"
for pno in (0, 2, 4):
    page = doc[pno]
    pix = page.get_pixmap(matrix=fitz.Matrix(2.2, 2.2))
    f = rf"{out}\sch_p{pno+1}.png"
    pix.save(f)
    print(f"  已渲染 {f}  ({pix.width}x{pix.height})")
print("\n=== POWER 页文本（前 120 行）===")
lines = [l.strip() for l in doc[0].get_text().splitlines() if l.strip()]
for l in lines[:120]:
    print("   ", l[:110])
doc.close()
