"""生成「任务页统一入口」的逐任务节点 → assets/resource/pipeline/taskrows.json

每个任务：<任务>(入口) → 公共_进入日常列表 → [Anchor]任务继续=<任务>_找行
  <任务>_找行：在日常列表里找这一行，找不到就下滚
  <任务>_行 → <任务>_前往（点前往，进入任务流程） / Flag_<任务>_今日已完成（领取或已领取）
  任务流程走完后回到 公共_进入日常列表 复核：这一行变成「领取/已领取」才算完成；
  仍是「前往」就再做一次（前往最多点 2 次）
新增任务时在 ROWS 里加一行，然后运行：python tools/gen_taskrows.py
"""
import json
from pathlib import Path

# 任务名, 列表里的行文字（正则）, 点「前往」后进入的节点
ROWS = [
    ("出行赠礼", "给任意角色赠送礼物", "出行赠礼_流程"),
    ("出行收礼", "在出行中收到礼物", "出行收礼_流程"),
]

LIST_ROI = [740, 70, 330, 620]
BTN_OFFSET = [280, -22, 150, 44]  # 行文字框 → 同一行右侧按钮区域


def build():
    d = {}
    for name, text, start in ROWS:
        d[name] = {
            "desc": f"任务入口：从任务页「日常」列表找到「{text}」",
            "anchor": {"任务继续": f"{name}_找行"},
            "next": ["公共_进入日常列表"],
            "focus": {"Node.Action.Starting": f"[color:Dimgray]开始：{name}[/color]"},
        }
        d[f"{name}_找行"] = {
            "timeout": 40000,
            "next": [f"{name}_行", "[JumpBack]公共_任务列表下滚"],
            "on_error": [f"{name}_未找到"],
        }
        d[f"{name}_行"] = {
            "recognition": {"type": "OCR", "param": {"expected": text, "roi": LIST_ROI}},
            "timeout": 5000,
            "next": [f"{name}_前往", f"Flag_{name}_今日已完成"],
            "on_error": [f"{name}_未找到"],
        }
        d[f"{name}_前往"] = {
            "recognition": {"type": "OCR", "param": {"expected": "前\\s*往", "roi": f"{name}_行", "roi_offset": BTN_OFFSET}},
            "desc": "点「前往」。只点按钮中间：行在列表最底下时按钮被裁掉一半，点到边缘会没反应",
            "action": {"type": "Click", "param": {"target_offset": [10, 4, -20, -12]}},
            "post_wait_freezes": {"time": 1000, "timeout": 15000},
            "max_hit": 2,
            "next": [start],
        }
        d[f"Flag_{name}_今日已完成"] = {
            "desc": "这一行已经是「领取」或「已领取」：今天已完成",
            "recognition": {"type": "OCR", "param": {"expected": "领\\s*取", "roi": f"{name}_行", "roi_offset": BTN_OFFSET}},
            "focus": {"Node.Action.Succeeded": f"[color:Limegreen]{name}今天已完成[/color]"},
        }
        d[f"{name}_未找到"] = {
            "focus": {"Node.Action.Succeeded": f"[color:Orange]任务列表里没有找到「{text}」，已跳过[/color]"},
        }
    return d


if __name__ == "__main__":
    out = Path(__file__).parent.parent / "assets/resource/pipeline/taskrows.json"
    out.write_text(json.dumps(build(), ensure_ascii=False, indent=4) + "\n", encoding="utf-8")
    print(f"written {out}")
