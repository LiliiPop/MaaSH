"""速写：按 tools/sketch/*.json 生成 assets/resource/pipeline/sketch.json 里由数据决定的节点，并写 assets/tasks/Sketch.json 的选项。

可以反复跑（幂等）：先删掉上次生成的节点，再按数据重新生成，其余手写节点原样保留。
  - 每道认得的题目（prompts.json）：速写_题_X、速写_灵_X_1~3、速写_连_X_中1~3、速写_连_X
  - 每张写真（gallery.json，30 张）：速写_赠_T_NPC / 速写_赠_T_男主（有偏好的才有）、速写_结果_T、速写_能力_T
  - 速写_赠_指定男主、速写_赠_默认
  - 速写_出题 / 速写_结果截图 / 速写_未知_结果截图 的 next
数据：
  gallery.json  地点 → 写真标题 → 3 个题材（灰机 wiki「校园/速写」图鉴）
  prompts.json  连线页左上「连接与 XX 相关」的 XX → 写真标题（note = 没实机核对过）
  icons.json    题材 → 图标模板（src=game 实机截的，在 image/sketch/灵感；src=wiki 灰机图标上色，在 image/sketch/wiki）
  prefs.json    题材偏好：男主 / NPC（灰机 wiki 表）
图标模板由 tools/gen_sketch_templates.py 生成。11-14 从设备上的生成结果反推重建（原脚本在容器重置时丢失），输出与 11-13 版逐节点一致。
"""
import collections
import json
import os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
P = os.path.join(ROOT, 'assets/resource/pipeline/sketch.json')
TP = os.path.join(ROOT, 'assets/tasks/Sketch.json')
DATA = os.path.join(ROOT, 'tools/sketch')
load = lambda n: json.load(open(os.path.join(DATA, n), encoding='utf-8'), object_pairs_hook=collections.OrderedDict)
gallery, prompts, icons, prefs = load('gallery.json'), load('prompts.json'), load('icons.json'), load('prefs.json')

GAME_SCALES = [60, 67, 75, 85, 92, 100, 108, 115, 125, 140, 150, 160]   # 实机图标缩放（%）
WIKI_WIDTHS = list(range(28, 81, 2))                                     # wiki 图标宽度（px）
TH = {'game': 0.65, 'wiki': 0.72}   # wiki 图标：实测真命中 0.66~0.81、误认最高 0.64
STUCK = '速写_卡住重开'
UNKNOWN = '速写_未知题目_截图'
SHORT = 15000
PROMPT_ROI = [20, 35, 470, 55]
TITLE_ROI = [500, 248, 340, 42]
SLOT_NAME = [[365, 246, 120, 36], [730, 246, 120, 36], [365, 370, 120, 36], [730, 370, 120, 36]]   # 赠送窗口 2×2 名字位置
# 7 个气泡固定位置里，只有这三对的连线会穿过正中 (680,348) 的气泡
OPPOSITE = [((494, 165), (897, 483)), ((536, 543), (845, 180)), ((345, 340), (1012, 305))]


def ocr(expected, roi):
    return {'type': 'OCR', 'param': {'expected': expected, 'roi': roi}}


def tm(theme, roi):
    ic = icons[theme]
    if ic['src'] == 'game':
        tpl = [f'sketch/灵感/{ic["file"]}_{s}.png' for s in GAME_SCALES]
    else:
        tpl = [f'sketch/wiki/{ic["file"]}_{w}.png' for w in WIKI_WIDTHS]
    return {'type': 'TemplateMatch', 'param': {'template': tpl, 'roi': roi, 'threshold': TH[ic['src']], 'green_mask': True, 'order_by': 'Score'}}


def slot(xy):
    return [xy[0] - 75, xy[1] - 75, 150, 150]


def gift_reco(names):
    rx = '^(' + '|'.join(sorted({n[:3] for n in names})) + ')'
    return {'type': 'And', 'param': {'all_of': [
        {'recognition': ocr('速写赠送', [420, 150, 450, 80])},
        {'recognition': {'type': 'Or', 'param': {'any_of': [{'recognition': ocr(rx, r)} for r in SLOT_NAME]}}}], 'box_index': 1}}


title2themes = collections.OrderedDict((t, th) for loc in gallery.values() for t, th in loc.items())
for p in prompts:
    assert p['title'] in title2themes, p
for th in title2themes.values():
    for x in th:
        assert x in icons, f'题材「{x}」没有图标'

# ---- 每道题目 ----
def chain(key, T, start, note_desc, final_reco, focus_text, nodes, on_err):
    """一条连线链：start 节点 → 灵_1~3（3 个题材图标）→ 连_中1~3（对角时换顺序）/ 连（一笔连完）。"""
    th = title2themes[T]
    L = [f'速写_灵_{key}_{i}' for i in (1, 2, 3)]
    start['next'] = [L[0]]
    for i in range(3):
        nodes[L[i]] = {
            'desc': f'题材「{th[i]}」的气泡（图标 {icons[th[i]]["file"]}）',
            'recognition': tm(th[i], [100, 90, 1100, 540]), 'action': 'DoNothing', 'timeout': 3000,
            'next': [L[i + 1]] if i < 2 else [f'速写_连_{key}_中1', f'速写_连_{key}_中2', f'速写_连_{key}_中3', f'速写_连_{key}'],
            'on_error': on_err}
    for k in range(3):   # 中k：另外两个在对角 → 第 k 个放中间
        a, b = [i for i in range(3) if i != k]
        ands = []
        for p0, p1 in OPPOSITE:
            for qa, qb in ((p0, p1), (p1, p0)):
                ands.append({'recognition': {'type': 'And', 'param': {'all_of': [
                    {'recognition': tm(th[a], slot(qa))}, {'recognition': tm(th[b], slot(qb))}]}}})
        nodes[f'速写_连_{key}_中{k + 1}'] = {
            'desc': f'「{th[a]}」「{th[b]}」在对角位置（直线会穿过正中间的气泡）：改成先连「{th[a]}」→「{th[k]}」→「{th[b]}」',
            'recognition': {'type': 'Or', 'param': {'any_of': ands}},
            'action': {'type': 'Swipe', 'param': {'begin': L[a], 'end': [L[k], L[b]], 'duration': [600, 600], 'end_hold': 200}},
            'post_delay': 800, 'max_hit': 1, 'next': ['速写_确定'], 'on_error': on_err}
    last = {'desc': f'「{T}」：从第 1 个气泡拖到第 2、第 3 个，一笔连完{note_desc}'}
    if final_reco:
        last['recognition'] = final_reco
    last.update({'action': {'type': 'Swipe', 'param': {'begin': L[0], 'end': [L[1], L[2]], 'duration': [600, 600], 'end_hold': 200}},
                 'post_delay': 800, 'max_hit': 1, 'timeout': 5000, 'next': ['速写_确定'], 'on_error': on_err,
                 'focus': {'Node.Action.Succeeded': focus_text}})
    nodes[f'速写_连_{key}'] = last


prompt_nodes = collections.OrderedDict()
for p in prompts:
    X, T = p['prompt'], p['title']
    th = title2themes[T]
    note = f'（{p["note"]}）' if p.get('note') else ''
    start = {'desc': f'题目「{X}」= 图鉴「{T}」，连 {"、".join(th)}{note}',
             'recognition': ocr(X, PROMPT_ROI), 'action': 'DoNothing', 'next': [], 'timeout': 3000, 'on_error': [UNKNOWN]}
    prompt_nodes[f'速写_题_{X}'] = start
    chain(X, T, start, '', ocr(X, PROMPT_ROI),
          f'[color:Dimgray]速写：题目「{X}」→「{T}」，连 {"、".join(th)}[/color]', prompt_nodes, [UNKNOWN])

# ---- 认不出题目时按图鉴猜（11-14）：截图后，看 30 张写真里哪一张的 3 个题材图标都在画面上，就按它连 ----
# 题库里已有题目的写真不猜（题目文字认得就不会走到这里）；全用实机图标的写真排前面（wiki 图标误认风险大一点）
known_titles = {p['title'] for p in prompts}
GUESS_ERR = ['速写_未知_清线', '速写_未知_连线_1']
guess_titles = [t for t in title2themes if t not in known_titles]
guess_titles.sort(key=lambda t: sum(icons[x]['src'] != 'game' for x in title2themes[t]))
guess_nodes = collections.OrderedDict()
for T in guess_titles:
    th = title2themes[T]
    start = {'desc': f'猜题：3 个题材（{"、".join(th)}）的图标都在画面上 → 按图鉴「{T}」连（题目文字不在题库里；连对是 S，猜错最多 B）',
             'recognition': {'type': 'And', 'param': {'all_of': [{'recognition': tm(x, [100, 90, 1100, 540])} for x in th]}},
             'action': 'DoNothing', 'next': [], 'timeout': 1000}
    guess_nodes[f'速写_猜_{T}'] = start
    chain(f'猜_{T}', T, start, '（按图标猜的）', None,
          f'[color:Deepskyblue]速写：题目不在题库里，按图标猜是「{T}」，连 {"、".join(th)}[/color]', guess_nodes, GUESS_ERR)

# ---- 每张写真：结果页认标题 → 能力页 → 赠送 ----
title_nodes = collections.OrderedDict()
pref_nodes = []
for t, th in title2themes.items():
    npcs = [n for n, pf in prefs['NPC'].items() if set(pf) & set(th)]
    men = [n for n, pf in prefs['男主'].items() if set(pf) & set(th)]
    gifts = []
    if npcs:
        gifts.append(f'速写_赠_{t}_NPC')
        title_nodes[f'速写_赠_{t}_NPC'] = {
            'desc': f'「{t}」（{"、".join(th)}）：先送偏好这些题材的 NPC（{"、".join(npcs)}）。任务选项「赠送对象」选「题材偏好优先」才启用',
            'enabled': False, 'recognition': gift_reco(npcs), 'action': 'Click', 'post_delay': 500, 'max_hit': 1,
            'next': ['速写_点击赠送'],
            'focus': {'Node.Action.Succeeded': '[color:Dimgray]速写赠送：画里有 NPC 偏好的题材，送给 NPC[/color]'}}
        pref_nodes.append(f'速写_赠_{t}_NPC')
    if men:
        gifts.append(f'速写_赠_{t}_男主')
        title_nodes[f'速写_赠_{t}_男主'] = {
            'desc': f'「{t}」：其次送偏好这些题材的男主（{"、".join(men)}）。「题材偏好优先」才启用',
            'enabled': False, 'recognition': gift_reco(men), 'action': 'Click', 'post_delay': 500, 'max_hit': 1,
            'next': ['速写_点击赠送'],
            'focus': {'Node.Action.Succeeded': '[color:Dimgray]速写赠送：送给偏好这些题材的男主[/color]'}}
        pref_nodes.append(f'速写_赠_{t}_男主')
    title_nodes[f'速写_结果_{t}'] = {
        'desc': f'结果页标题是「{t}」：点屏幕进能力页',
        'recognition': {'type': 'And', 'param': {'all_of': [
            {'recognition': ocr('速写结果', [420, 120, 450, 120])}, {'recognition': ocr(f'^{t}$', TITLE_ROI)}]}},
        'action': {'type': 'Click', 'param': {'target': [600, 625, 80, 20]}},
        'post_wait_freezes': {'time': 600, 'timeout': 4000, 'rate_limit': 200}, 'max_hit': 1, 'timeout': SHORT,
        'next': [f'速写_能力_{t}'] + gifts + ['速写_赠_指定男主', '速写_赠_默认'], 'on_error': [STUCK]}
    title_nodes[f'速写_能力_{t}'] = {
        'desc': '能力页（画技、造型、张力……）：点屏幕进赠送',
        'recognition': {'type': 'And', 'param': {'all_of': [
            {'recognition': ocr('速写结果', [420, 120, 450, 120])}, {'recognition': ocr('画技', [300, 395, 700, 40])}]}},
        'action': {'type': 'Click', 'param': {'target': [600, 625, 80, 20]}},
        'post_wait_freezes': {'time': 600, 'timeout': 4000, 'rate_limit': 200}, 'max_hit': 2, 'timeout': SHORT,
        'next': gifts + ['速写_赠_指定男主', '速写_赠_默认', f'速写_能力_{t}'], 'on_error': [STUCK]}
title_nodes['速写_赠_指定男主'] = {
    'desc': '送给「速写地点」里选的男主（选了男主时启用；名字在选项里改）',
    'enabled': False, 'recognition': gift_reco(['艾因']), 'action': 'Click', 'post_delay': 500, 'max_hit': 1,
    'next': ['速写_点击赠送'],
    'focus': {'Node.Action.Succeeded': '[color:Dimgray]速写赠送：送给指定的男主[/color]'}}
title_nodes['速写_赠_默认'] = {
    'desc': '没有指定男主、或指定的男主不在这个地点：不改选择（默认选中第一位），直接点「赠送」',
    'recognition': ocr('速写赠送', [420, 150, 450, 80]), 'pre_delay': 800, 'action': 'DoNothing',
    'next': ['速写_点击赠送'], 'timeout': SHORT, 'on_error': [STUCK]}

# ---- 合进 sketch.json：删旧的生成节点，新节点放回原来的位置 ----
d = json.load(open(P, encoding='utf-8'), object_pairs_hook=collections.OrderedDict)
def is_prompt_node(k):
    return k.startswith(('速写_题_', '速写_灵_', '速写_连_', '速写_猜_'))
def is_title_node(k):
    return k.startswith(('速写_赠_', '速写_能力_')) or (k.startswith('速写_结果_') and k[len('速写_结果_'):] in title2themes)
out = collections.OrderedDict()
placed_p = placed_t = False
for k, v in d.items():
    if is_prompt_node(k):
        if not placed_p:
            out.update(prompt_nodes); out.update(guess_nodes); placed_p = True
        continue
    if is_title_node(k):
        if not placed_t:
            out.update(title_nodes); placed_t = True
        continue
    if k == STUCK and not placed_t:
        out.update(title_nodes); placed_t = True
    out[k] = v
if not placed_p:   # 第一次生成：题目节点放在「出题」后面
    o2 = collections.OrderedDict()
    for k, v in out.items():
        o2[k] = v
        if k == '速写_出题':
            o2.update(prompt_nodes); o2.update(guess_nodes)
    out = o2
out['速写_出题']['next'] = [f'速写_题_{p["prompt"]}' for p in prompts] + [UNKNOWN]
out[UNKNOWN]['next'] = [f'速写_猜_{t}' for t in guess_titles] + ['速写_未知_清线', '速写_未知_连线_1']
out[UNKNOWN]['focus'] = {'Node.Action.Succeeded': '[color:Orange]速写：题目还不在题库里，已截图；按图标猜写真，猜不出就把所有气泡连起来（A 级）[/color]'}
for n in ('速写_结果截图', '速写_未知_结果截图'):
    out[n]['next'] = [f'速写_结果_{t}' for t in title2themes] + ['速写_结果退出']

# ---- 任务选项（assets/tasks/Sketch.json）----
task = json.load(open(TP, encoding='utf-8'), object_pairs_hook=collections.OrderedDict)
MEN = list(prefs['男主'])
def man_gift(m):
    return {'enabled': True, 'recognition': gift_reco([m])}
loc_cases = []
for m in MEN:
    loc_cases.append({'name': f'男主·{m}', 'pipeline_override': {
        '速写_选地点': {'recognition': {'type': 'And', 'param': {'all_of': [
            {'recognition': ocr('退出速写', [1090, 640, 190, 80])},
            {'recognition': {'type': 'TemplateMatch', 'param': {'template': f'sketch/男主/{m}.png', 'roi': [0, 85, 1280, 545], 'threshold': 0.85, 'order_by': 'Score'}}}],
            'box_index': 1}}},
        '速写_赠_指定男主': man_gift(m)}})
for loc in gallery:
    loc_cases.append({'name': f'地点·{loc}', 'pipeline_override': {
        '速写_选地点': {'recognition': {'type': 'And', 'param': {'all_of': [
            {'recognition': ocr('退出速写', [1090, 640, 190, 80])}, {'recognition': ocr(f'^{loc}$', [0, 90, 1280, 560])}], 'box_index': 1}}}}})
counts = '、'.join(f'{loc} {len(v)} 张' for loc, v in gallery.items())
opts = collections.OrderedDict()
opts['速写地点'] = {'type': 'select', 'label': '速写地点', 'default_case': '地点·港口',
    'description': f'选男主：在校园地图上认男主头像（男主每天站的地点不固定），点他所在的地点；选地点：直接点地点名。<br>地点里的写真：{counts}。',
    'cases': loc_cases}
opts['速写赠送'] = {'type': 'select', 'label': '赠送对象', 'default_case': '送给男主',
    'description': '<b>送给男主</b>：送给「速写地点」里选的那位男主（选的是地点时，送给赠送窗口默认选中的第一位）。<br><b>题材偏好优先</b>：画里有 NPC 偏好的题材就送那位 NPC；没有就送偏好这些题材的男主；都没有再按「送给男主」送。（偏好表来自灰机 wiki）',
    'cases': [{'name': '送给男主'}, {'name': '题材偏好优先', 'pipeline_override': {n: {'enabled': True} for n in pref_nodes}}]}
opts['速写练习方向'] = task['option']['速写练习方向']
task['option'] = opts
task['task'][0]['option'] = list(opts)

json.dump(task, open(TP, 'w', encoding='utf-8'), ensure_ascii=False, indent=4)
open(TP, 'a', encoding='utf-8').write('\n')
json.dump(out, open(P, 'w', encoding='utf-8'), ensure_ascii=False, indent=4)
open(P, 'a', encoding='utf-8').write('\n')
print('题库', len(prompts), '道：', '、'.join(p['prompt'] for p in prompts))
print('写真', len(title2themes), '张；偏好节点', len(pref_nodes), '个')
