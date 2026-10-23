"""体检工具：扫一遍 maafw.log，统计每个识别节点命中 / 失败次数，以及命中时框是不是贴着 ROI 边。
用法：python tools/scan_logs.py <maafw.log...>
输出：命中位置贴框边（<6px，换号/换主题时容易出框）和日志里从没命中过的节点。
10-24：配合「多路认法」一起用——每次实机测完跑一下，看有没有新的贴边节点要放宽。"""
import re, json, glob, sys, collections
from pathlib import Path
P = {}
for f in glob.glob(str(Path(__file__).parent.parent / 'assets/resource/pipeline/*.json')):
    P.update(json.load(open(f, encoding='utf-8')))
succ = collections.defaultdict(list); fail = collections.Counter()
for f in sys.argv[1:]:
    for l in open(f, encoding='utf-8', errors='replace'):
        if 'msg=Node.Recognition.' not in l: continue
        m = re.search(r'"name":"([^"]*)","reco_details":\{"algorithm":"([A-Za-z]+)","box":(null|\[[0-9,]+\])', l)
        if not m: continue
        n, alg, box = m.groups()
        if 'Recognition.Succeeded' in l: succ[n].append(json.loads(box) if box != 'null' else None)
        elif 'Recognition.Failed' in l: fail[n] += 1
for n, v in P.items():
    r = v.get('recognition')
    if not isinstance(r, dict) or r.get('type') not in ('OCR', 'TemplateMatch'): continue
    roi = r.get('param', {}).get('roi')
    if n not in succ or not roi or len(roi) != 4: continue
    x, y, w, h = roi
    m = min([min(b[0]-x, b[1]-y, x+w-b[0]-b[2], y+h-b[1]-b[3]) for b in succ[n] if b and b != roi] or [99])
    if m < 6: print(f'贴边 {m:>3}px  {n}  roi={roi}  命中{len(succ[n])}次')
for n in sorted(fail, key=lambda k: -fail[k]):
    if n in P and n not in succ: print(f'从没命中  {n}  失败{fail[n]}次')
