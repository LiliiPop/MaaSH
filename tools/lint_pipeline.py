"""MaaSH 流程自检：补 JSON Schema 查不出来、但会让流程跑错的问题。

用法：python tools/lint_pipeline.py
有问题时列出来并以非 0 退出。检查：
  1. And / Or 的子项必须写成 {"recognition": {...}}。
     少了这层包装时，子项会被当成「直接命中」，导致乱点（10-21 月卡每周购买差点踩到）。
  2. next / on_error / 选项里引用的节点都存在。
  3. roi / target 引用的节点都存在。
  4. 模板图文件都存在；没被任何节点用到的模板图列为提醒。
  5. 同一个节点名不在多个文件里重复定义。
"""
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "assets", "resource")
errors, warnings = [], []

nodes, where = {}, {}
for f in sorted(glob.glob(os.path.join(RES, "pipeline", "*.json"))):
    name = os.path.basename(f)
    for k, v in json.load(open(f, encoding="utf-8")).items():
        if k in nodes:
            errors.append(f"节点重复定义：{k}（{where[k]} 和 {name}）")
        nodes[k], where[k] = v, name

tasks = {}
for f in sorted(glob.glob(os.path.join(ROOT, "assets", "tasks", "*.json"))):
    tasks[os.path.basename(f)] = json.load(open(f, encoding="utf-8"))

templates_used = set()


def strip(ref):
    if isinstance(ref, dict):
        ref = ref.get("name", "")
    return re.sub(r"^(\[[^\]]*\])+", "", ref)


def walk(o, owner, known):
    if isinstance(o, dict):
        if o.get("type") in ("And", "Or") and isinstance(o.get("param"), dict):
            for sub in o["param"].get("all_of", []) + o["param"].get("any_of", []):
                if isinstance(sub, dict) and "recognition" not in sub:
                    errors.append(f"{owner}：And/Or 子项缺少 \"recognition\" 包装，会被当成直接命中")
        for key, v in o.items():
            if key in ("next", "on_error") and isinstance(v, list):
                for ref in v:
                    if isinstance(ref, str) and ref.startswith("[Anchor]"):
                        continue  # 锚点名由 anchor 字段动态指向，不是节点名
                    if strip(ref) not in known:
                        errors.append(f"{owner}：{key} 引用了不存在的节点 {strip(ref)}")
            elif key in ("roi", "target") and isinstance(v, str) and v not in known:
                errors.append(f"{owner}：{key} 引用了不存在的节点 {v}")
            elif key == "template":
                for t in v if isinstance(v, list) else [v]:
                    templates_used.add(t)
                    if not os.path.exists(os.path.join(RES, "image", t)):
                        errors.append(f"{owner}：模板图不存在 image/{t}")
            walk(v, owner, known)
    elif isinstance(o, list):
        for x in o:
            walk(x, owner, known)


known = set(nodes)
for k, v in nodes.items():
    walk(v, f"{where[k]}:{k}", known)

for fname, d in tasks.items():
    for t in d.get("task", []):
        if t["entry"] not in known:
            errors.append(f"{fname}：入口节点 {t['entry']} 不存在")
    for oname, opt in d.get("option", {}).items():
        for case in opt.get("cases", []):
            for k, v in case.get("pipeline_override", {}).items():
                if k not in known:
                    errors.append(f"{fname}：选项「{oname}/{case['name']}」改写了不存在的节点 {k}")
                walk(v, f"{fname}:{oname}/{case['name']}", known)

for p in glob.glob(os.path.join(RES, "image", "**", "*.png"), recursive=True):
    rel = os.path.relpath(p, os.path.join(RES, "image")).replace("\\", "/")
    if rel not in templates_used:
        warnings.append(f"模板图没被用到：image/{rel}")

for w in warnings:
    print("提醒：" + w)
for e in errors:
    print("错误：" + e)
print(f"检查了 {len(nodes)} 个节点、{len(tasks)} 个任务文件：{len(errors)} 个错误，{len(warnings)} 个提醒")
sys.exit(1 if errors else 0)
