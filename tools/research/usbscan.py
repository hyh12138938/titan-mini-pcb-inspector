import pymupdf, re
p = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\docs\Titan_Mini_schematic_v1.0.pdf"
doc = pymupdf.open(p)
for i, pg in enumerate(doc):
    t = pg.get_text()
    hits = sorted(set(re.findall(r"USB[A-Z0-9_]*|CH340|CP210\d|FT232|VBUS|D\+|D-|OTG", t)))
    if hits: print(f"p{i+1:02d}: {','.join(hits[:12])}")
