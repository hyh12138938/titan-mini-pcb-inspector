import re
from pypdf import PdfReader
p = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\docs\Titan_Mini_schematic_v1.0.pdf"
r = PdfReader(p)
print("pages", len(r.pages))
txt = []
for i, pg in enumerate(r.pages):
    try:
        t = pg.extract_text() or ""
    except Exception as e:
        t = ""
    txt.append((i + 1, t))
full = "\n".join(t for _, t in txt)
print("chars", len(full))
open(r"D:\RTT\_re\schematic.txt", "w", encoding="utf-8").write(full)
for kw in ["TXD1", "RXD1", "40P", "PIN8", "PIN10", "GND"]:
    print(kw, full.count(kw))
for i, t in txt:
    if "TXD1" in t or "40P" in t:
        print("=== page", i, "===")
        print(t[:1600])
