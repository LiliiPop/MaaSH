"""从 maafw.log 统计每个任务、每一步花了多少时间，找出「卡」在哪里。

用法：python tools/timeline.py <maafw.log> [更多 log…] [--task 出行赠礼] [--top 8]
输出：每次任务运行的总用时，以及耗时最长的几步（某个节点开始到下一个节点开始的间隔）。
节点「识别超时」（Failed）也会列出，通常就是等了 timeout 才放弃的地方。
"""
import argparse
import re
from datetime import datetime

ap = argparse.ArgumentParser()
ap.add_argument("logs", nargs="+")
ap.add_argument("--task", default="", help="只看入口名包含这个词的任务")
ap.add_argument("--top", type=int, default=8)
a = ap.parse_args()

runs, cur = [], None
for f in a.logs:
    for line in open(f, encoding="utf-8", errors="replace"):
        if "run_task] task start" in line:
            m = re.search(r'"entry":"([^"]*)"', line)
            cur = {"entry": m.group(1) if m else "?", "t0": line[1:24], "steps": [], "fails": []}
            runs.append(cur)
            continue
        if cur is None or "msg=Node.PipelineNode." not in line:
            continue
        m = re.search(r"msg=Node\.PipelineNode\.(\w+)", line)
        n = re.search(r'"name":"([^"]*)"', line)
        t = datetime.strptime(line[1:24], "%Y-%m-%d %H:%M:%S.%f")
        if m.group(1) == "Starting":
            cur["steps"].append((t, n.group(1) if n else ""))
        elif m.group(1) == "Failed":
            cur["fails"].append(n.group(1) if n else "")

for r in runs:
    if a.task not in r["entry"] or r["entry"].startswith("recognition/") or not r["steps"]:
        continue
    st = r["steps"]
    total = (st[-1][0] - st[0][0]).total_seconds()
    gaps = sorted(((st[i + 1][0] - st[i][0]).total_seconds(), st[i][1]) for i in range(len(st) - 1))[::-1]
    print(f"\n== {r['t0'][5:19]}  {r['entry']}  共 {total:.0f} 秒，{len(st)} 步")
    for g, name in gaps[: a.top]:
        if g >= 2:
            print(f"   {g:6.1f} 秒  {name}")
    if r["fails"]:
        from collections import Counter
        print("   超时放弃：" + "，".join(f"{k}×{v}" for k, v in Counter(r["fails"]).most_common(6)))
