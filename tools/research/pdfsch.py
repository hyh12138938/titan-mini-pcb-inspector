from pypdf import PdfReader
p = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\docs\Titan_Mini_schematic_v1.0.pdf"
r = PdfReader(p)
txt = "\n".join((pg.extract_text() or "") for pg in r.pages)
open(r"D:\RTT\_re\schematic.txt","w",encoding="utf-8").write(txt)
print(f"schematic pages={len(r.pages)} chars={len(txt)}")
