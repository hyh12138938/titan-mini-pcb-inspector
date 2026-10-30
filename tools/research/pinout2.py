import re
from pypdf import PdfReader
for name in [r"D:\RTT\sdk-bsp-ra8p1-titan-mini\docs\Titan_Mini_datasheet.pdf"]:
    r = PdfReader(name)
    print("###", name, "pages", len(r.pages))
    for i, pg in enumerate(r.pages):
        try:
            t = pg.extract_text() or ""
        except Exception:
            continue
        if re.search(r"PIN\s*8|PIN\s*10|TXD1|RXD1|40P", t):
            print("=== page", i + 1, "===")
            print(t[:1200])
