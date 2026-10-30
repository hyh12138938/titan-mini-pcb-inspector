import fitz, os, re
p = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\docs\Titan_Mini_schematic_v1.0.pdf"
doc = fitz.open(p)
outdir = r"D:\RTT\_re\sch"
os.makedirs(outdir, exist_ok=True)
print("pages:", len(doc))
for i, page in enumerate(doc):
    t = page.get_text()
    hits = sorted(set(re.findall(r"LCD_[A-Z0-9]+|DISP_[A-Z0-9]+|CONN|FPC|HDR", t)))
    mark = " <<< LCD" if any(k.startswith("LCD_") for k in hits) else ""
    print(f"p{i+1:02d} chars={len(t):5d} keys={','.join(hits[:8])}{mark}")
