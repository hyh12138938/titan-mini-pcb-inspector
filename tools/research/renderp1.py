import pymupdf
doc = pymupdf.open(r"D:\RTT\sdk-bsp-ra8p1-titan-mini\docs\Titan_Mini_schematic_v1.0.pdf")
pix = doc[0].get_pixmap(matrix=pymupdf.Matrix(3.2,3.2))
out = r"D:\RTT\_re\sch\power_p01.png"
pix.save(out); print("saved", out, pix.width, "x", pix.height)
