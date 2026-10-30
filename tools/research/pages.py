from pypdf import PdfReader
p = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\docs\Titan_Mini_schematic_v1.0.pdf"
r = PdfReader(p)
for i, pg in enumerate(r.pages):
    t = pg.extract_text() or ""
    tags = []
    for kw in ("INTERFACE", "TXD1", "RXD1", "CONN-SMD", "J6", "GND"):
        if kw in t:
            tags.append(kw)
    title = ""
    if "Title:" in t:
        head = t.split("Title:")[1][:80].replace("\n", " ")
        title = head
    print("page %2d  %-45s  %s" % (i + 1, ",".join(tags), title))
