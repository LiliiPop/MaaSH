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

# 任务名, 列表里的行文字（正则）, 点「前往」后进入的节点, 这一行文字框的宽度（实机 OCR 量的）
ROWS = [
    ("出行赠礼", "给任意角色赠送礼物", "出行赠礼_流程", 207),
    ("出行收礼", "在出行中收到礼物", "出行收礼_准备", 220),
    ("画灵提升", "升级任意画灵", "画灵_流程", 175),
    ("绘卷提升", "升级任意绘卷", "绘卷_流程", 179),
    ("手偶剧场", "手偶剧场点赞", "剧场_流程", 177),
]

LIST_ROI = [740, 70, 330, 620]
BOTTOM_ROI = [740, 600, 330, 95]  # 列表最底下一行：按钮会被裁掉一半
# 行文字框 → 同一行右侧按钮区域。文字框左边在 x≈760，按钮在 x≈1070~1142；
# 10-27 实机：原来区域往右放宽 150，行在底部时把右下角浮着的「一键领取」也框进来了（x≈1197），
# 认成这一行「领取」= 今天已完成（绘卷提升没做却标了完成）→ 区域右边界固定到 x≈1180（宽度按每行文字框宽度算）
BTN_RIGHT = 1180
def btn_offset(width):
    return [280, -22, (BTN_RIGHT - 760 - 280) - width, 44]


def build():
    d = {}
    for name, text, start, width in ROWS:
        BTN_OFFSET = btn_offset(width)
        d[name] = {
            "desc": f"任务入口：从任务页「日常」列表找到「{text}」",
            "anchor": {"任务继续": f"{name}_找行"},
            "next": ["公共_进入日常列表"],
            "focus": {"Node.Action.Starting": f"[color:Dimgray]开始：{name}[/color]"},
        }
        d[f"{name}_找行"] = {
            "desc": "在日常列表里找这一行，找不到就往下滚一屏。10-24：每个任务用自己的下滚节点（最多 7 次，日常列表约 12 行、每次滚约 1.4 行，7 次能到底），滚完还没有就 6 秒后算没找到（原来共用一个最多 10 次的下滚，找不到时还要再干等 40 秒）",
            "timeout": 6000,
            "next": [f"[JumpBack]{name}_行_太靠下", f"{name}_行", f"[JumpBack]{name}_下滚"],
            "on_error": [f"{name}_未找到"],
        }
        d[f"{name}_行_太靠下"] = {
            "desc": "10-27：这一行在列表最底下（按钮被裁掉一半，认不出「前往」，还容易和右下角「一键领取」挨在一起）：列表再往上推一小段，让这一行露全（最多 2 次，列表到底推不动就按原位置判断）",
            "recognition": {"type": "OCR", "param": {"expected": text, "roi": BOTTOM_ROI}},
            "action": {"type": "Swipe", "param": {"begin": [900, 520, 20, 20], "end": [900, 380, 20, 20], "duration": 400}},
            "max_hit": 2,
            "post_wait_freezes": {"time": 500, "timeout": 1500, "rate_limit": 200},
        }
        d[f"{name}_下滚"] = {
            "desc": "在「今日任务」页把右侧列表往下滚一段（只给这一个任务计次数）",
            "recognition": {"type": "OCR", "param": {"expected": "今日任务", "roi": [220, 80, 260, 85]}},
            "action": {"type": "Swipe", "param": {"begin": [900, 560, 20, 20], "end": [900, 300, 20, 20], "duration": 400}},
            "max_hit": 7,
            "post_wait_freezes": {"time": 500, "timeout": 1500, "rate_limit": 200},
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
