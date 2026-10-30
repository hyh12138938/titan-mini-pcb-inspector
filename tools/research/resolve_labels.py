# -*- coding: utf-8 -*-
"""解析 plugin.xml 里的 %key，用 plugin.properties + nl_zh 语言包替换成 英文/中文 标签。"""
import os, re, io, glob
import xml.etree.ElementTree as ET

RE = r'D:\RTT\_re'
PLUG = os.path.join(RE, 'plugins')
PROPS = os.path.join(RE, 'props')
OUT = os.path.join(RE, 'labels.md')


def load_props(path):
    """Java properties: ISO-8859-1 + \\uXXXX 转义"""
    d = {}
    if not os.path.isfile(path):
        return d
    raw = open(path, 'rb').read()
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith(b'#') or line.startswith(b'!'):
            continue
        if b'=' not in line:
            continue
        k, v = line.split(b'=', 1)
        try:
            s = v.decode('latin-1')
        except Exception:
            continue
        s = re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m.group(1), 16)), s)
        d[k.decode('latin-1').strip()] = s.strip()
    return d


def norm(s):
    return re.sub(r'_\d+\.\d+\.\d+.*$', '', s)


def bundle_dirs():
    for name in sorted(os.listdir(PLUG)):
        yield name


# 收集：bundle -> {key: en}, bundle -> {key: zh}
en, zh, names = {}, {}, {}
pdir_map = {norm(d): d for d in os.listdir(PROPS)}
for b in bundle_dirs():
    px = os.path.join(PLUG, b, 'plugin.xml')
    pdir = os.path.join(PROPS, b)
    p = load_props(os.path.join(pdir, 'plugin.properties'))
    if p:
        en[b] = p
    if b.endswith('.nl_zh'):
        zh[b[:-6]] = p            # 去掉 .nl_zh
    # MANIFEST 里的 Bundle-Name
    mf = os.path.join(PLUG, b, 'META-INF', 'MANIFEST.MF')
    if os.path.isfile(mf):
        for line in open(mf, 'r', encoding='utf-8', errors='replace').read().splitlines():
            if line.startswith('Bundle-Name:'):
                names[b] = line.split(':', 1)[1].strip()
            elif line.startswith('Bundle-Version:') and b not in names:
                names[b] = line.split(':', 1)[1].strip()

out = ['# RT-Thread Studio 标签解析（plugin.xml %key → EN/ZH）\n']

out.append('## 各 bundle 的 Bundle-Name\n')
for b in sorted(names):
    out.append(f'- `{b}` → {names[b]}')

out.append('\n## 命令 / 编辑器 / 向导 / 启动配置（已解析标签）\n')

KEYREF = re.compile(r'%([\w.\-]+)')

for b in sorted(os.listdir(PLUG)):
    px = os.path.join(PLUG, b, 'plugin.xml')
    if not os.path.isfile(px):
        continue
    if not (b.startswith('org.rt-thread') or b.startswith('ilg.gnumcueclipse.debug.gdbjtag')):
        continue
    try:
        root = ET.parse(px).getroot()
    except Exception:
        continue

    rows = []
    for ext in root:
        point = (ext.get('point') or '').split('.')[-1]
        if point not in {'commands', 'editors', 'newWizards', 'launchConfigurationTypes',
                         'importWizards', 'preferencePages', 'propertyPages',
                         'launchConfigurationTabGroups', 'perspectives', 'views',
                         'contentTypes', 'natures', 'builders', 'menus'}:
            continue
        for k in ext:
            cid = k.get('id') or k.get('commandId')
            label = k.get('name') or k.get('label')
            if not cid:
                continue
            m = KEYREF.match(label or '')
            key = m.group(1) if m else None
            e = en.get(b, {}).get(key or '', label if not key else '')
            z = zh.get(b, {}).get(key or '', '')
            if not e and not key:
                e = label or ''
            rows.append((point, cid, e, z))

    if rows:
        out.append(f'\n### `{b}`\n')
        out.append('| 类型 | ID | EN | 中文 |')
        out.append('|---|---|---|---|')
        seen = set()
        for point, cid, e, z in rows:
            if (point, cid) in seen:
                continue
            seen.add((point, cid))
            out.append(f'| {point} | `{cid}` | {e or ""} | {z or ""} |')

with io.open(OUT, 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))

print('written', OUT, os.path.getsize(OUT))
print('bundles with en props:', len(en), '| zh packages:', len(zh))
