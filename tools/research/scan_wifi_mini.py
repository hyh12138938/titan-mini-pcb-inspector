import re
import fitz
p = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\docs\Titan_Mini_schematic_v1.0.pdf"
doc = fitz.open(p)
pat = re.compile(r"(CYW\d+|AW-CU\d+|AW_CU\d+|43438|43439|WIFI|WLAN|SDIO|CYW94343)", re.I)
hits = {}
for i in range(doc.page_count):
    t = doc[i].get_text()
    for m in pat.findall(t):
        hits.setdefault(m.upper(), set()).add(i + 1)
print("  Titan Mini 原理图中 WiFi 相关标识：")
if hits:
    for k in sorted(hits):
        print(f"    {k:12s} 页 {sorted(hits[k])}")
else:
    print("    (无)  → Mini 板原理图未见 WiFi 模组")
doc.close()
