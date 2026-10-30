import re, sys, os
from pypdf import PdfReader

base = r'D:\RTT\sdk-bsp-ra8p1-titan-mini\docs'
out = r'D:\RTT\_re'
for name in ['Titan_Mini_schematic_v1.0.pdf', 'Titan_Mini_user_manual.pdf', 'Titan_Mini_datasheet.pdf']:
    p = os.path.join(base, name)
    r = PdfReader(p)
    txt = []
    for pg in r.pages:
        try:
            txt.append(pg.extract_text() or '')
        except Exception:
            txt.append('')
    alltxt = '\n'.join(txt)
    op = os.path.join(out, name + '.txt')
    with open(op, 'w', encoding='utf-8') as f:
        f.write(alltxt)
    print('#####', name, 'pages', len(r.pages), 'chars', len(alltxt))
    for kw in ['RTL', 'PHY', 'RJ45', '以太网', '网口', 'Ethernet', 'WIFI', 'WiFi', 'ESP', 'RW007', 'SDIO', 'SDRAM', 'MRAM', 'USB']:
        print('   ', kw, alltxt.count(kw))
