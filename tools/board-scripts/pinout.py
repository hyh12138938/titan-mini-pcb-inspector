import re
from pypdf import PdfReader
p = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\docs\Titan_Mini_user_manual.pdf"
r = PdfReader(p)
print("pages", len(r.pages))
for i, pg in enumerate(r.pages[:40]):
    try:
        t = pg.extract_text() or ""
    except Exception:
        continue
    if re.search(r"PIN\s*8|PIN\s*10|TXD|RXD|40P|GND", t):
        print("=== page", i + 1, "===")
        print(t[:1500])
