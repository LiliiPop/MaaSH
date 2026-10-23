"""检查「JumpBack 进去的节点，顺着 next/on_error 又走回了调用它的循环节点」——这会嵌套出第二层循环，
里层做完后外层还在等（10-24 画展完成后任务不结束就是这个原因）。用法：python tools/check_nesting.py"""
import json, glob
d = {}
for f in glob.glob('assets/resource/pipeline/*.json'):
    d.update(json.load(open(f, encoding='utf-8')))
def edges(n):
    v = d.get(n, {}); out = []
    for key in ('next', 'on_error'):
        r = v.get(key, []); r = [r] if isinstance(r, str) else r
        out += [x if isinstance(x, str) else x.get('name') for x in r]
    return out
bad = 0
for X in d:
    for e in edges(X):
        if not e.startswith('[JumpBack]'):
            continue
        seen, stack = set(), [(e[10:], [e[10:]])]
        while stack:
            n, path = stack.pop()
            if n in seen: continue
            seen.add(n)
            for z in edges(n):
                if z.startswith('[JumpBack]') or z.startswith('[Anchor]'): continue
                if z == X:
                    print(f'{X}  ⇢JB  ' + ' → '.join(path + [z])); bad += 1
                elif z in d and not z.startswith('公共_'):
                    stack.append((z, path + [z]))
print('有问题的条数：', bad)
