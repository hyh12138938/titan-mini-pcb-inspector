import re
import fitz
p = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\docs\Titan_Mini_schematic_v1.0.pdf"
doc = fitz.open(p)
pat = re.compile(r"(RTL8\d{3}|LAN87\d{2}|DP838\d{2}|YT8\d{3}|KSZ9\d{3}|KSZ8081|88E\d{4}|PHY\d*|RJ45|HR911\d*)", re.I)
print("  原理图里与以太网相关的标识：")
seen = {}
for i in range(doc.page_count):
    t = doc[i].get_text()
    for m in pat.findall(t):
        seen.setdefault(m.upper(), set()).add(i + 1)
for k in sorted(seen):
    print(f"    {k:12s} 出现在页 {sorted(seen[k])}")
if not seen:
    print("    (未找到 PHY/网口 标识)")
doc.close()
