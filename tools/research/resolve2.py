# -*- coding: utf-8 -*-
"""plugin.xml 的 %key → 英文/中文标签。直接从 props 目录反向匹配 PLUG 目录。"""
import os, re, io
import xml.etree.ElementTree as ET

RE = r'D:\RTT\_re'
PLUG = os.path.join(RE, 'plugins')
PROPS = os.path.join(RE, 'props')
OUT = os.path.join(RE, 'labels.md')

KEYREF = re.compile(r'%([\w.\-]+)')


def load_props(path):
    d = {}
    if not os.path.isfile(path):
        return d
    raw = open(path, 'rb').read()
    for line in raw.splitlines():
        line = line.strip()
        if not line or line[:1] in (b'#', b'!'):
            continue
        if b'=' not in line:
            continue
        k, v = line.split(b'=', 1)
        s = v.decode('latin-1')
        s = re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m.group(1), 16)), s)
        d[k.decode('latin-1').strip()] = s.strip()
    return d


# 英文 / 中文 properties（props 目录名已剥离版本号）
en, zh = {}, {}
for d in sorted(os.listdir(PROPS)):
    p = os.path.join(PROPS, d, 'plugin.properties')
    props = load_props(p)
    if not props:
        continue
    if d.endswith('.nl_zh'):
        zh[d[:-6]] = props
    else:
        en[d] = props
print('en bundles:', len(en), 'zh bundles:', len(zh))
if en:
    sample = sorted(en)[0]
    print('sample:', sample, '→', list(en[sample].items())[:3])

# MANIFEST 名
names = {}
for b in sorted(os.listdir(PLUG)):
    mf = os.path.join(PLUG, b, 'META-INF', 'MANIFEST.MF')
    if os.path.isfile(mf):
        txt = open(mf, 'r', encoding='utf-8', errors='replace').read()
        m = re.search(r'Bundle-Name:\s*(.+)', txt)
        v = re.search(r'Bundle-Version:\s*(.+)', txt)
        names[b] = (m.group(1).strip() if m else '') + (' @' + v.group(1).strip() if v else '')

out = ['# RT-Thread Studio 标签解析（plugin.xml %key → EN / 中文）\n']

out.append('\n## Bundle 清单（Bundle-Name @Version）\n')
for b in sorted(names):
    out.append(f'- `{b}` → {names[b]}')

out.append('\n## 命令 / 编辑器 / 向导 / 启动配置\n')

for b in sorted(os.listdir(PLUG)):
    px = os.path.join(PLUG, b, 'plugin.xml')
    if not os.path.isfile(px):
        continue
    if not (b.startswith('org.rt-thread') or b.startswith('ilg.gnumcueclipse.debug.gdbjtag')):
        continue
    base = re.sub(r'_\d+\.\d+\.\d+.*$', '', b)
    E, Z = en.get(base, {}), zh.get(base, {})
    try:
        root = ET.parse(px).getroot()
    except Exception:
        continue

    rows, seen = [], set()
    for ext in root:
        point = (ext.get('point') or '').split('.')[-1]
        if point not in {'commands', 'editors', 'newWizards', 'launchConfigurationTypes',
                         'importWizards', 'preferencePages', 'propertyPages',
                         'perspectives', 'views', 'natures', 'builders'}:
            continue
        for k in ext:
            cid = k.get('id') or k.get('commandId')
            if not cid:
                continue
            raw = k.get('name') or k.get('label') or ''
            m = KEYREF.match(raw)
            if m:
                key = m.group(1)
                e, z = E.get(key, ''), Z.get(key, '')
            else:
                e, z = raw, ''
            if (point, cid) in seen:
                continue
            seen.add((point, cid))
            rows.append((point, cid, e, z))

    if rows:
        out.append(f'\n### `{b}`\n')
        out.append('| 类型 | ID | EN | 中文 |')
        out.append('|---|---|---|---|')
        for point, cid, e, z in rows:
            out.append(f'| {point} | `{cid}` | {e} | {z} |')

with io.open(OUT, 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))
print('written', OUT, os.path.getsize(OUT), 'bytes')
