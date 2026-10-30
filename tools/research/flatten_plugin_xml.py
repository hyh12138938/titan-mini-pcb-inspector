# -*- coding: utf-8 -*-
"""把 Eclipse 插件的 plugin.xml 拍平成可读目录：扩展点 / 命令 / 菜单 / 视图 / 向导 / 启动配置。"""
import os, re, io
import xml.etree.ElementTree as ET

SRC = r'D:\RTT\_re\plugins'
OUT = r'D:\RTT\_re\catalog.md'

interest_children = {
    'command', 'menuContribution', 'handler', 'view', 'editor', 'perspective',
    'wizard', 'page', 'workingSet', 'launchConfigurationType', 'launchShortcut',
    'decorator', 'propertyPage', 'propertyTester', 'contentType', 'builder',
    'nature', 'natures', 'runtime', 'definition', 'category', 'toolbar',
    'key', 'binding', 'markerResolutionGenerator', 'problemMarker',
}
attr_keep = ('id', 'name', 'label', 'class', 'commandId', 'categoryId',
             'menubarPath', 'toolbarPath', 'locationURI', 'defaultHandler',
             'description', 'point', 'type', 'mode', 'category', 'allowsPlatform')

lines = []
stats = {}

for bundle in sorted(os.listdir(SRC)):
    px = os.path.join(SRC, bundle, 'plugin.xml')
    if not os.path.isfile(px):
        continue
    try:
        root = ET.parse(px).getroot()
    except Exception as e:
        lines.append(f'\n## {bundle}\n\n!! XML 解析失败: {e}\n')
        continue

    lines.append(f'\n## {bundle}\n')
    for ext in root:
        point = ext.get('point', '?')
        short = point.split('.')[-1]
        stats[short] = stats.get(short, 0) + 1
        kids = [c for c in ext if c.tag in interest_children]
        if not kids:
            continue
        # 只保留有点信息量的扩展点
        if short not in {'commands', 'menus', 'handlers', 'views', 'editors', 'perspectives',
                         'newWizards', 'preferencePages', 'launchConfigurationTypes',
                         'launchShortcuts', 'propertyPages', 'builders', 'natures',
                         'contentTypes', 'activities', 'contexts', 'key', 'bindings'}:
            continue
        lines.append(f'### `{point}`')
        for k in kids:
            attrs = []
            for a in attr_keep:
                v = k.get(a)
                if v and a != 'point':
                    attrs.append(f'{a}="{v}"')
            if attrs:
                lines.append('- **' + k.tag + '** ' + ' '.join(attrs))
            for sub in k:
                sa = ' '.join(f'{a}="{sub.get(a)}"' for a in attr_keep if sub.get(a))
                if sa:
                    lines.append(f'    - {sub.tag} {sa}')
        lines.append('')

lines.insert(0, '# RT-Thread Studio 插件扩展点目录（自动生成）\n')
lines.insert(1, '生成来源: ' + SRC + '\n')
top = sorted(stats.items(), key=lambda kv: -kv[1])[:30]
lines.insert(2, '扩展点统计: ' + ', '.join(f'{k}={v}' for k, v in top) + '\n')

with io.open(OUT, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

print('written', OUT, os.path.getsize(OUT), 'bytes')
print('sections', sum(1 for l in lines if l.startswith('## ')))
