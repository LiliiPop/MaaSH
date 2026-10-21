"""生成「🍰清体力」的流程节点和任务选项。

    python tools/gen_sweep.py
      → assets/resource/pipeline/sweep.json
      → assets/tasks/Sweep.json

流程（截图见 WorkfieldScreenshots/sweep、shop/02_*、03_*）：
  主界面「练习」→ 日常练习页点关卡 →（画材收罗 / 梦之旅途：点子关卡，看今天开没开）
  → 选难度（标签会被 OCR 连成一行，所以先把标签栏滑到头再点固定位置，用「N体力」核对）
  → 预检：按单次消耗 c、倍数 m（双倍干劲符 ×2）、体力档 B 算出次数 N=ceil(B/(c·m))，
    读右上角体力是否 ≥ N·c·m（用正则比较大小）
  → 点「画灵入战」，确保是「连续战斗」版的快速通关弹窗 → 选符
     · 用符：弹窗里把次数调到 N →「快速过关」→ 恭喜获得
     · 暂不使用：「连续作战」→ 连续战斗弹窗选「战斗次数」调到 N →「确定」
       → 编队（助战空位就点盾牌、选列表第一个）→「连续战斗」→ 战斗（手动就改自动）→ 结算
  → 回任务页看「累计消耗60点体力」这一行是否可领 → Flag_清体力_今日已完成

不能做算术的地方都在这里提前算好写进节点；次数用锚点（anchor）带到后面的弹窗。
"""
import json
import math
from pathlib import Path

ROOT = Path(__file__).parent.parent
PW = {"time": 500, "timeout": 1500, "rate_limit": 200}
PW_SLOW = {"time": 500, "timeout": 3000, "rate_limit": 200}

COSTS = [8, 10, 12, 14, 18]          # 单次消耗（作战演练难度5是18）
BUDGETS = [60, 120]
MULTS = [1, 2]                        # 双倍干劲符 ×2
MAX_N = max(math.ceil(b / (c * m)) for b in BUDGETS for c in COSTS for m in MULTS)

STAGE_ROI = [940, 520, 130, 45]       # 「画灵入战」
COST_ROI = [960, 565, 120, 45]        # 「14体力」
STAMINA_ROI = [700, 30, 115, 40]      # 右上「117/166」
LIST_ROI = [740, 70, 330, 620]        # 任务页日常列表
BTN_OFFSET = [280, -22, 150, 44]
QUICK_FIELD = [455, 505, 75, 40]      # 快速通关弹窗：次数
QUICK_MINUS, QUICK_PLUS, QUICK_MAX = [415, 508, 36, 34], [536, 508, 36, 34], [602, 508, 40, 34]
QUICK_BTN = [740, 495, 200, 50]       # 「112 快速过关」/「连续作战」
CONT_FIELD = [785, 378, 65, 38]       # 连续战斗弹窗：战斗次数
CONT_MINUS, CONT_PLUS = [742, 382, 30, 30], [863, 380, 30, 30]
BLANK = [600, 670, 80, 20]            # 弹窗外下方空白
RESULT_BLANK = [600, 20, 80, 30]      # 结算页上方空白（下方右侧有培养按钮，避开）


def ocr(expected, roi, **kw):
    p = {"expected": expected, "roi": roi}
    p.update(kw)
    return {"type": "OCR", "param": p}


def sub(rec):
    return {"recognition": rec}


def ge_regex(x):
    """匹配 ≥x 的非负整数（不超过 4 位）。"""
    s = str(x)
    alts = [s]
    for i, ch in enumerate(s):
        d = int(ch)
        if d < 9:
            rest = len(s) - i - 1
            alts.append(s[:i] + (f"[{d + 1}-9]" if d < 8 else "9") + ("\\d" * rest if rest else ""))
    alts.append(f"[1-9]\\d{{{len(s)},3}}")
    return "(?:" + "|".join(alts) + ")"


def int_set(nums):
    return "^(?:" + "|".join(str(n) for n in sorted(nums)) + ")$"


def build():
    d = {}
    page_rec = ocr("画灵入战", STAGE_ROI)

    # ---------- 入口：练习 → 关卡 ----------
    cinema = json.loads((ROOT / "assets/resource/pipeline/cinema.json").read_text(encoding="utf-8"))
    open_practice = json.loads(json.dumps(cinema["电影院_打开练习"]))
    open_practice["desc"] = "主界面「练习」（全景在底部，默认主题在右侧）"
    open_practice["next"] = ["清体力_进关卡"]

    d["清体力"] = {
        "desc": "任务入口：练习 → 关卡 → 选难度 → 按选项刷到 60/120 体力 → 回任务页确认「累计消耗60点体力」",
        "timeout": 60000,
        "next": ["[JumpBack]公共_稍后再说", "[JumpBack]公共_晚点再说", "清体力_打开练习", "[JumpBack]公共_返回主界面"],
        "on_error": ["公共_任务失败"],
        "focus": {"Node.Action.Starting": "[color:Dimgray]开始：清体力[/color]"},
    }
    d["清体力_打开练习"] = open_practice
    d["清体力_进关卡"] = {
        "desc": "日常练习页点关卡卡片（由选项「清体力关卡」改写文字）",
        "recognition": ocr("星间剧场", [180, 200, 820, 330]),
        "action": {"type": "Click"},
        "post_wait_freezes": PW_SLOW, "timeout": 15000,
        "next": ["清体力_关卡页"], "on_error": ["公共_任务失败"],
    }
    d["清体力_关卡页"] = {
        "desc": "关卡页已打开（画材收罗 / 梦之旅途由选项改成先选子关卡）",
        "recognition": page_rec, "timeout": 10000,
        "next": ["清体力_选难度"], "on_error": ["公共_任务失败"],
    }

    # ---------- 子关卡（画材收罗 / 梦之旅途） ----------
    d["清体力_子关卡_点"] = {
        "desc": "点底部的子关卡圆按钮（位置由选项改写）",
        "recognition": page_rec,
        "action": {"type": "Click", "param": {"target": [128, 547, 40, 40]}},
        "post_wait_freezes": PW,
        "next": ["清体力_子关卡_确认"],
    }
    d["清体力_子关卡_确认"] = {
        "desc": "标题变成选定的子关卡（文字由选项改写）",
        "recognition": ocr("海底打击乐团", [640, 145, 470, 75]),
        "timeout": 5000,
        "next": ["清体力_今天开放", "清体力_今天未开放"],
        "on_error": ["清体力_子关卡没找到"],
    }
    d["清体力_今天开放"] = {
        "desc": "开放的关卡右下有「连续战斗」勾选框；没开放的没有",
        "recognition": ocr("连续战斗", [650, 520, 130, 40]),
        "next": ["清体力_选难度"],
    }
    d["清体力_今天未开放"] = {
        "recognition": page_rec,
        "focus": {"Node.Action.Succeeded": "[color:Orange]所选子关卡今天没开放，清体力已跳过（开放日见任务设置说明）[/color]"},
    }
    d["清体力_子关卡没找到"] = {
        "focus": {"Node.Action.Succeeded": "[color:Red]没切到所选子关卡，清体力已跳过[/color]"},
    }

    # ---------- 难度 ----------
    d["清体力_选难度"] = {
        "desc": "先把难度标签栏滑到头（选项决定往哪边），再点固定位置",
        "recognition": page_rec,
        "action": {"type": "Swipe", "param": {"begin": [1070, 300, 10, 10], "end": [700, 300, 10, 10], "duration": 300}},
        "post_wait_freezes": PW,
        "next": ["清体力_点难度"],
    }
    d["清体力_点难度"] = {
        "desc": "点难度标签（位置由选项改写）",
        "recognition": page_rec,
        "action": {"type": "Click", "param": {"target": [995, 290, 40, 28]}},
        "post_wait_freezes": PW,
        "next": ["清体力_难度确认"],
    }
    d["清体力_难度确认"] = {
        "desc": "用「N体力」核对切到了所选难度（由选项改写）；对不上就当作未解锁",
        "recognition": ocr("^(?:14|18)\\s*体力$", COST_ROI),
        "timeout": 4000,
        "next": ["清体力_倍数"],
        "on_error": ["清体力_难度未解锁"],
    }
    d["清体力_难度未解锁"] = {
        "focus": {"Node.Action.Succeeded": "[color:Red]所选难度未解锁（或没切过去），清体力已跳过[/color]"},
    }

    # ---------- 预检：次数和体力 ----------
    d["清体力_倍数"] = {"desc": "按道具符选项分到 ×1 / ×2（由选项改写）", "next": ["清体力_倍数_1"]}
    for m in MULTS:
        d[f"清体力_倍数_{m}"] = {
            "desc": f"×{m}：按体力档分到各单次消耗（由选项「体力档」改写）",
            "next": [f"清体力_预检_60_{m}_{c}" for c in COSTS],
            "on_error": ["清体力_消耗没认出"],
        }
        for b in BUDGETS:
            for c in COSTS:
                n = math.ceil(b / (c * m))
                total = n * c * m
                d[f"清体力_预检_{b}_{m}_{c}"] = {
                    "desc": f"单次 {c} 体力 ×{m}：刷 {n} 次共 {total}（≥{b}）",
                    "recognition": ocr(f"^{c}\\s*体力$", COST_ROI),
                    "next": [f"清体力_体力够_{b}_{m}_{c}", f"清体力_体力不够_{b}_{m}_{c}"],
                }
                d[f"清体力_体力够_{b}_{m}_{c}"] = {
                    "desc": f"右上体力 ≥ {total}",
                    "recognition": ocr(f"^{ge_regex(total)}\\s*/", STAMINA_ROI),
                    "anchor": {"快次数": f"清体力_快_{n}", "连次数": f"清体力_连_{n}"},
                    "next": ["清体力_开弹窗"],
                    "focus": {"Node.Action.Succeeded": f"[color:Dimgray]体力够：刷 {n} 次，共消耗 {total}[/color]"},
                }
                d[f"清体力_体力不够_{b}_{m}_{c}"] = {
                    "desc": f"体力不到 {total}",
                    "anchor": {"一次门槛": f"清体力_够一次_{m}_{c}"},
                    "next": ["清体力_补充入口"],
                    "focus": {"Node.Action.Succeeded": f"[color:Orange]体力不够刷满 {b}（需要 {total}）[/color]"},
                }
    for m in MULTS:
        for c in COSTS:
            d[f"清体力_够一次_{m}_{c}"] = {
                "recognition": ocr(f"^{ge_regex(c * m)}\\s*/", STAMINA_ROI),
                "next": ["清体力_不足策略"],
            }
    d["清体力_消耗没认出"] = {
        "focus": {"Node.Action.Succeeded": "[color:Red]没认出关卡页的单次体力消耗，清体力已跳过[/color]"},
    }

    # ---------- 体力不足 ----------
    d["清体力_补充入口"] = {"desc": "选项「自动使用体力道具」打开时先去补体力", "next": ["清体力_不足分流"]}
    d["清体力_不足分流"] = {"next": ["[Anchor]一次门槛", "清体力_一次都不够"]}
    d["清体力_不足策略"] = {"desc": "由选项「体力不足时」改写", "next": ["清体力_不足跳过"]}
    d["清体力_不足跳过"] = {
        "focus": {"Node.Action.Succeeded": "[color:Orange]体力不够，按设置跳过清体力[/color]"},
    }
    d["清体力_不足清完"] = {
        "anchor": {"快次数": "清体力_快_最大", "连次数": "清体力_连_耗尽"},
        "next": ["清体力_开弹窗"],
        "focus": {"Node.Action.Succeeded": "[color:Dimgray]按设置清完当前体力[/color]"},
    }
    d["清体力_一次都不够"] = {
        "focus": {"Node.Action.Succeeded": "[color:Orange]体力连一次都不够，清体力已结束[/color]"},
    }
    d["清体力_补_打开"] = {
        "desc": "点右上体力旁的「+」打开「补充体力」（最多 3 次）",
        "recognition": ocr("\\d+\\s*/\\s*\\d+", STAMINA_ROI),
        "action": {"type": "Click", "param": {"target": [812, 36, 28, 30]}},
        "max_hit": 3, "post_wait_freezes": PW,
        "next": ["清体力_补_只剩钻石", "清体力_补_用道具"],
    }
    d["清体力_补_只剩钻石"] = {
        "desc": "钻石排在道具最后；正中间是「钻石」= 已经没有体力道具 → 点空白取消，绝不买",
        "recognition": {"type": "And", "param": {"all_of": [
            sub(ocr("补充体力", [520, 160, 240, 65])),
            sub(ocr("^钻\\s*石$", [575, 440, 130, 45]))]}},
        "action": {"type": "Click", "param": {"target": BLANK}},
        "post_wait_freezes": PW,
        "next": ["清体力_不足分流"],
        "focus": {"Node.Action.Succeeded": "[color:Orange]没有体力道具了（只剩钻石），不补体力[/color]"},
    }
    d["清体力_补_用道具"] = {
        "desc": "有体力道具：点「确定」使用（默认选中第一个道具）",
        "recognition": ocr("补充体力", [520, 160, 240, 65]),
        "action": {"type": "Click", "param": {"target": [730, 508, 175, 40]}},
        "post_wait_freezes": PW_SLOW,
        "next": ["清体力_补_用后"],
        "focus": {"Node.Action.Succeeded": "[color:Deepskyblue]使用体力道具补充体力[/color]"},
    }
    d["清体力_补_用后"] = {
        "desc": "回到关卡页后重新预检",
        "timeout": 8000,
        "next": ["[JumpBack]公共_获得奖励", "[JumpBack]公共_点击空白继续", "清体力_补_回关卡"],
        "on_error": ["公共_任务失败"],
    }
    d["清体力_补_回关卡"] = {"recognition": page_rec, "next": ["清体力_倍数"]}

    # ---------- 弹窗 ----------
    d["清体力_开弹窗"] = {
        "desc": "点「画灵入战」",
        "recognition": page_rec,
        "action": {"type": "Click"},
        "post_wait_freezes": PW, "max_hit": 3, "timeout": 5000,
        "next": ["清体力_连续弹窗", "清体力_非连续弹窗", "清体力_意外补充体力"],
        "on_error": ["公共_任务失败"],
    }
    d["清体力_非连续弹窗"] = {
        "desc": "没勾连续战斗时的弹窗（按钮是「开始作战」）：关掉，去勾「连续战斗」",
        "recognition": ocr("每次作战消耗一张", [380, 245, 520, 40]),
        "action": {"type": "Click", "param": {"target": BLANK}},
        "post_wait_freezes": PW, "max_hit": 2,
        "next": ["清体力_勾连续"],
    }
    d["清体力_勾连续"] = {
        "desc": "勾「连续战斗」，会直接弹出连续版的快速通关弹窗",
        "recognition": ocr("连续战斗", [650, 520, 130, 40]),
        "action": {"type": "Click", "param": {"target": [652, 532, 22, 26]}},
        "post_wait_freezes": PW, "timeout": 5000,
        "next": ["清体力_连续弹窗"], "on_error": ["公共_任务失败"],
    }
    d["清体力_意外补充体力"] = {
        "desc": "点「画灵入战」弹出了「补充体力」（体力不够一次）：点空白取消",
        "recognition": ocr("补充体力", [520, 160, 240, 65]),
        "action": {"type": "Click", "param": {"target": BLANK}},
        "focus": {"Node.Action.Succeeded": "[color:Orange]体力不够，已取消补充体力弹窗，清体力已结束[/color]"},
    }
    d["清体力_连续弹窗"] = {
        "desc": "连续版的快速通关弹窗（「使用道具可进行快速过关，或依然可选择连续战斗」）",
        "recognition": ocr("依然可选择连续战斗", [380, 245, 520, 40]),
        "next": ["清体力_选符"],
    }
    d["清体力_选符"] = {
        "desc": "点所选的符 / 暂不使用（文字由选项改写）",
        "recognition": ocr("^超强助力符$", [395, 425, 500, 45]),
        "action": {"type": "Click", "param": {"target": True, "target_offset": [0, -50, 0, 0]}},
        "post_wait_freezes": PW,
        "next": ["清体力_快速模式", "清体力_符不够"],
    }
    d["清体力_快速模式"] = {
        "recognition": ocr("快速过关", QUICK_BTN),
        "next": ["[Anchor]快次数"],
    }
    d["清体力_连战模式"] = {
        "recognition": ocr("连续作战", QUICK_BTN),
        "action": {"type": "Click"},
        "post_wait_freezes": PW, "timeout": 5000,
        "next": ["清体力_连战弹窗"], "on_error": ["公共_任务失败"],
    }
    d["清体力_符不够"] = {
        "desc": "选了符，按钮却不是「快速过关」→ 多半是符用完了。为了不误入实际战斗，直接结束",
        "recognition": ocr("连续作战|开始作战", QUICK_BTN),
        "action": {"type": "Click", "param": {"target": BLANK}},
        "focus": {"Node.Action.Succeeded": "[color:Orange]所选道具符不够了，清体力已跳过[/color]"},
    }
    d["清体力_非预期"] = {
        "desc": "选了暂不使用，按钮却是「快速过关」→ 没切过去，结束",
        "recognition": ocr("快速过关", QUICK_BTN),
        "action": {"type": "Click", "param": {"target": BLANK}},
        "focus": {"Node.Action.Succeeded": "[color:Red]没能切到「暂不使用」，清体力已跳过[/color]"},
    }
    d["清体力_连战弹窗"] = {
        "desc": "连续战斗弹窗：至体力耗尽 / 战斗次数",
        "recognition": ocr("战斗次数", [365, 365, 160, 50]),
        "next": ["[Anchor]连次数"],
    }

    # 快速通关弹窗里调次数
    d["清体力_快_最大"] = {
        "desc": "清完当前体力：点「⤒」最大次数",
        "recognition": ocr("快速过关", QUICK_BTN),
        "action": {"type": "Click", "param": {"target": QUICK_MAX}},
        "post_wait_freezes": PW,
        "next": ["清体力_点快速过关"],
    }
    d["清体力_连_耗尽"] = {
        "desc": "清完当前体力：勾「至体力耗尽」",
        "recognition": ocr("至体力耗尽", [365, 290, 180, 45]),
        "action": {"type": "Click", "param": {"target": [372, 308, 24, 24]}},
        "post_wait_freezes": PW,
        "next": ["清体力_连战确定"],
    }
    for n in range(1, MAX_N + 1):
        smaller, bigger = list(range(1, n)), list(range(n + 1, 100))
        # 快速通关弹窗
        d[f"清体力_快_{n}"] = {"desc": f"把次数调到 {n}", "next": [f"清体力_快_{n}_好"] + ([f"清体力_快_{n}_加"] if smaller else []) + [f"清体力_快_{n}_减", f"清体力_快_{n}_卡住"]}
        d[f"清体力_快_{n}_好"] = {
            "recognition": ocr(f"^{n}$", QUICK_FIELD),
            "next": ["清体力_点快速过关"],
        }
        if smaller:
            d[f"清体力_快_{n}_加"] = {
                "recognition": ocr(int_set(smaller), QUICK_FIELD),
                "action": {"type": "Click", "param": {"target": QUICK_PLUS}},
                "max_hit": MAX_N + 2, "post_wait_freezes": {"time": 200, "timeout": 1000, "rate_limit": 100},
                "next": [f"清体力_快_{n}"],
            }
        d[f"清体力_快_{n}_减"] = {
            "recognition": ocr(int_set(bigger), QUICK_FIELD),
            "action": {"type": "Click", "param": {"target": QUICK_MINUS}},
            "max_hit": 120, "post_wait_freezes": {"time": 200, "timeout": 1000, "rate_limit": 100},
            "next": [f"清体力_快_{n}"],
        }
        d[f"清体力_快_{n}_卡住"] = {
            "desc": "次数调不到目标（体力或符不够）→ 关弹窗结束",
            "action": {"type": "Click", "param": {"target": BLANK}},
            "focus": {"Node.Action.Succeeded": f"[color:Orange]次数调不到 {n}（体力或道具符不够），清体力已跳过[/color]"},
        }
        # 连续战斗弹窗
        d[f"清体力_连_{n}"] = {
            "desc": f"勾「战斗次数」，调到 {n}",
            "recognition": ocr("战斗次数", [365, 365, 160, 50]),
            "action": {"type": "Click", "param": {"target": [372, 383, 24, 24]}},
            "post_wait_freezes": PW,
            "next": [f"清体力_连_{n}_调"],
        }
        d[f"清体力_连_{n}_调"] = {"next": [f"清体力_连_{n}_好"] + ([f"清体力_连_{n}_加"] if smaller else []) + [f"清体力_连_{n}_减", f"清体力_连_{n}_卡住"]}
        d[f"清体力_连_{n}_好"] = {
            "recognition": ocr(f"^{n}$", CONT_FIELD),
            "next": ["清体力_连战确定"],
        }
        if smaller:
            d[f"清体力_连_{n}_加"] = {
                "recognition": ocr(int_set(smaller), CONT_FIELD),
                "action": {"type": "Click", "param": {"target": CONT_PLUS}},
                "max_hit": MAX_N + 2, "post_wait_freezes": {"time": 200, "timeout": 1000, "rate_limit": 100},
                "next": [f"清体力_连_{n}_调"],
            }
        d[f"清体力_连_{n}_减"] = {
            "recognition": ocr(int_set(bigger), CONT_FIELD),
            "action": {"type": "Click", "param": {"target": CONT_MINUS}},
            "max_hit": 120, "post_wait_freezes": {"time": 200, "timeout": 1000, "rate_limit": 100},
            "next": [f"清体力_连_{n}_调"],
        }
        d[f"清体力_连_{n}_卡住"] = {
            "action": {"type": "Click", "param": {"target": [415, 497, 140, 40]}},
            "focus": {"Node.Action.Succeeded": f"[color:Orange]战斗次数调不到 {n}，清体力已跳过[/color]"},
        }

    # ---------- 快速过关 ----------
    d["清体力_点快速过关"] = {
        "recognition": ocr("快速过关", QUICK_BTN),
        "action": {"type": "Click"},
        "post_wait_freezes": PW_SLOW,
        "next": ["清体力_快速等奖励"],
        "focus": {"Node.Action.Succeeded": "[color:Deepskyblue]快速过关[/color]"},
    }
    d["清体力_快速等奖励"] = {
        "timeout": 20000,
        "next": ["[JumpBack]公共_获得奖励", "[JumpBack]公共_点击空白继续", "清体力_意外补充体力", "清体力_回到关卡"],
        "on_error": ["公共_任务失败"],
    }

    # ---------- 实际战斗 ----------
    d["清体力_连战确定"] = {
        "recognition": ocr("确\\s*定", [760, 485, 120, 55]),
        "action": {"type": "Click"},
        "post_wait_freezes": PW_SLOW, "timeout": 5000,
        "next": ["清体力_编队"], "on_error": ["公共_任务失败"],
    }
    d["清体力_编队"] = {
        "desc": "编队页",
        "recognition": ocr("编队", [100, 5, 160, 70]),
        "timeout": 15000,
        "next": ["清体力_点助战空位", "清体力_开始连战", "清体力_意外补充体力"],
        "on_error": ["公共_任务失败"],
    }
    d["清体力_点助战空位"] = {
        "desc": "第二格是助战空位（盾牌）：点开助战列表",
        "recognition": {"type": "TemplateMatch", "param": {"template": "sweep/助战空位.png", "roi": [250, 140, 185, 450], "threshold": 0.8}},
        "action": {"type": "Click"},
        "post_wait_freezes": PW, "max_hit": 3,
        "next": ["清体力_选助战"],
    }
    d["清体力_选助战"] = {
        "desc": "助战选择：点列表第一个",
        "recognition": ocr("助战选择", [140, 75, 190, 55]),
        "action": {"type": "Click", "param": {"target": [100, 140, 70, 75]}},
        "post_wait_freezes": PW, "timeout": 8000,
        "next": ["清体力_编队"], "on_error": ["公共_任务失败"],
    }
    d["清体力_开始连战"] = {
        "desc": "编队右下「连续战斗」",
        "recognition": ocr("连续战斗", [985, 610, 235, 60]),
        "action": {"type": "Click"},
        "post_wait_freezes": PW_SLOW, "max_hit": 2,
        "next": ["清体力_战斗中"],
        "focus": {"Node.Action.Succeeded": "[color:Deepskyblue]开始连续战斗（要等播片和战斗，时间较长）[/color]"},
    }
    d["清体力_战斗中"] = {
        "desc": "等战斗：手动就改自动；胜利结算点上方空白继续；失败就结束；回到关卡页 = 打完",
        "timeout": 300000,
        "next": ["清体力_战斗失败", "[JumpBack]清体力_改自动", "[JumpBack]清体力_战斗胜利",
                 "[JumpBack]公共_获得奖励", "[JumpBack]公共_点击空白继续", "清体力_回到关卡"],
        "on_error": ["公共_任务失败"],
    }
    d["清体力_改自动"] = {
        "desc": "右上角是「手动」→ 点一下改成自动",
        "recognition": ocr("^手动$", [1150, 20, 90, 40]),
        "action": {"type": "Click"},
        "max_hit": 10,
        "focus": {"Node.Action.Succeeded": "[color:Dimgray]战斗切到自动[/color]"},
    }
    d["清体力_战斗胜利"] = {
        "recognition": ocr("完美通关|通关(?!失败)|胜利", [640, 100, 560, 170]),
        "action": {"type": "Click", "param": {"target": RESULT_BLANK}},
        "max_hit": MAX_N * 3, "post_wait_freezes": PW_SLOW,
    }
    d["清体力_战斗失败"] = {
        "recognition": ocr("通关失败", [640, 100, 560, 170]),
        "action": {"type": "Click", "param": {"target": RESULT_BLANK}},
        "focus": {"Node.Action.Succeeded": "[color:Red]战斗失败，没拿到奖励，清体力已跳过——可能需要检查配队[/color]"},
    }
    d["清体力_回到关卡"] = {
        "recognition": page_rec,
        "anchor": {"任务继续": "清体力_找行"},
        "next": ["公共_进入日常列表"],
        "focus": {"Node.Action.Succeeded": "[color:Dimgray]清体力打完，回任务页确认[/color]"},
    }

    # ---------- 回任务页确认 ----------
    d["清体力_找行"] = {
        "timeout": 40000,
        "next": ["清体力_行", "[JumpBack]公共_任务列表下滚"],
        "on_error": ["清体力_未找到行"],
    }
    d["清体力_行"] = {
        "recognition": ocr("累计消耗60点体力", LIST_ROI),
        "timeout": 5000,
        "next": ["Flag_清体力_今日已完成", "清体力_未达成"],
        "on_error": ["清体力_未找到行"],
    }
    d["Flag_清体力_今日已完成"] = {
        "desc": "「累计消耗60点体力」这一行是「领取 / 已领取」",
        "recognition": ocr("领\\s*取", "清体力_行", roi_offset=BTN_OFFSET),
        "focus": {"Node.Action.Succeeded": "[color:Limegreen]清体力完成：累计消耗60点体力已达成[/color]"},
    }
    d["清体力_未达成"] = {
        "recognition": ocr("前\\s*往", "清体力_行", roi_offset=BTN_OFFSET),
        "focus": {"Node.Action.Succeeded": "[color:Orange]刷完了，但「累计消耗60点体力」还没完成[/color]"},
    }
    d["清体力_未找到行"] = {
        "focus": {"Node.Action.Succeeded": "[color:Orange]任务列表里没找到「累计消耗60点体力」[/color]"},
    }
    return d


# ---------- 任务选项 ----------
SUB_STAGES = {
    "画材收罗": ("画材属性", "画材收罗的属性关卡", [
        ("张力", "海底打击乐团", [128, 547, 40, 40], "周一、三、五、日"),
        ("色彩", "扶起墨水瓶", [260, 568, 40, 40], "周二、四、六、日"),
        ("造型", "铅笔刀的逆反", [390, 572, 40, 40], "周二、四、六、日"),
        ("情感", "盒子里的猫", [520, 547, 40, 40], "周一、三、五、日"),
    ]),
    "梦之旅途": ("梦之旅途角色", "梦之旅途的角色关卡", [
        ("叶瑄", "无穷雪境", [98, 553, 40, 40], "周一、四、六、日"),
        ("艾因", "剑术征程", [216, 571, 40, 40], "周一、三、五、日"),
        ("路辰", "守护之旅", [325, 571, 40, 40], "周二、四、六、日"),
        ("罗夏", "鸢尾之战", [444, 571, 40, 40], "周一、三、五、日"),
        ("司岚", "法师塔巡查", [553, 547, 40, 40], "周二、四、六、日"),
    ]),
}
# 难度标签：滑到最左时 1–4 的位置；难度5 要滑到最右
DIFF = {
    1: ("left", [680, 290, 40, 28], "^8\\s*体力$"),
    2: ("left", [775, 290, 40, 28], "^10\\s*体力$"),
    3: ("left", [873, 290, 40, 28], "^12\\s*体力$"),
    4: ("left", [970, 290, 40, 28], "^14\\s*体力$"),
    5: ("right", [995, 290, 40, 28], "^(?:14|18)\\s*体力$"),
}
SWIPE = {
    "left": {"begin": [700, 300, 10, 10], "end": [1070, 300, 10, 10], "duration": 300},
    "right": {"begin": [1070, 300, 10, 10], "end": [700, 300, 10, 10], "duration": 300},
}


def options():
    o = {}
    stage_cases = []
    for name in ["星间剧场", "画材收罗", "梦之旅途", "作战演练"]:
        ov = {"清体力_进关卡": {"recognition": ocr(name, [180, 200, 820, 330])}}
        case = {"name": name, "pipeline_override": ov}
        if name in SUB_STAGES:
            ov["清体力_关卡页"] = {"next": ["清体力_子关卡_点"]}
            case["option"] = [SUB_STAGES[name][0]]
        stage_cases.append(case)
    o["清体力关卡"] = {
        "type": "select",
        "description": "在哪个关卡刷。画材收罗、梦之旅途还要选子关卡，子关卡只在固定的几天开放，没开放的那天会自动跳过。",
        "default_case": "星间剧场",
        "cases": stage_cases,
    }
    for stage, (opt, label, subs) in SUB_STAGES.items():
        o[opt] = {
            "type": "select",
            "description": f"{label}。⚠️ 每个只在固定的几天开放，当天没开放会自动跳过（日志里有提示）。",
            "default_case": subs[0][0],
            "cases": [{
                "name": n,
                "description": f"「{t}」，{days}开放",
                "pipeline_override": {
                    "清体力_子关卡_点": {"action": {"type": "Click", "param": {"target": tgt}}},
                    "清体力_子关卡_确认": {"recognition": ocr(t, [640, 145, 470, 75])},
                },
            } for n, t, tgt, days in subs],
        }
    o["清体力难度"] = {
        "type": "select",
        "description": "每次消耗：难度1 8、难度2 10、难度3 12、难度4 14、难度5 14（作战演练难度5 是 18）。所选难度未解锁会报错并跳过。",
        "default_case": "难度5",
        "cases": [{
            "name": f"难度{k}",
            "pipeline_override": {
                "清体力_选难度": {"action": {"type": "Swipe", "param": SWIPE[side]}},
                "清体力_点难度": {"action": {"type": "Click", "param": {"target": tgt}}},
                "清体力_难度确认": {"recognition": ocr(cost, COST_ROI)},
            },
        } for k, (side, tgt, cost) in DIFF.items()],
    }
    o["道具符"] = {
        "type": "select",
        "description": "用符会「快速过关」，不用打；「暂不使用」会进入实际战斗（要等播片和战斗，自动选第一个助战，失败会跳过并提示检查配队）。",
        "default_case": "超强助力符",
        "cases": [
            {"name": "超强助力符", "description": "消耗不变，额外奖励",
             "pipeline_override": {"清体力_选符": {"recognition": ocr("^超强助力符$", [395, 425, 500, 45]), "next": ["清体力_快速模式", "清体力_符不够"]},
                                   "清体力_倍数": {"next": ["清体力_倍数_1"]}}},
            {"name": "双倍干劲符", "description": "消耗 ×2",
             "pipeline_override": {"清体力_选符": {"recognition": ocr("^双倍干劲符$", [395, 425, 500, 45]), "next": ["清体力_快速模式", "清体力_符不够"]},
                                   "清体力_倍数": {"next": ["清体力_倍数_2"]}}},
            {"name": "暂不使用（实际战斗）",
             "pipeline_override": {"清体力_选符": {"recognition": ocr("^暂不使用$", [395, 425, 500, 45]), "next": ["清体力_连战模式", "清体力_非预期"]},
                                   "清体力_倍数": {"next": ["清体力_倍数_1"]}}},
        ],
    }
    o["体力档"] = {
        "type": "select",
        "description": "至少消耗多少体力。按次数向上取整，所以会刚好达到或略超过（例如难度5 每次 14，选 60 会刷 5 次共 70）。",
        "default_case": "60",
        "cases": [{
            "name": str(b),
            "pipeline_override": {f"清体力_倍数_{m}": {"next": [f"清体力_预检_{b}_{m}_{c}" for c in COSTS]} for m in MULTS},
        } for b in BUDGETS],
    }
    o["体力不足时"] = {
        "type": "select",
        "description": "当前体力不够刷满所选体力档时怎么办。",
        "default_case": "跳过清体力",
        "cases": [
            {"name": "跳过清体力", "pipeline_override": {"清体力_不足策略": {"next": ["清体力_不足跳过"]}}},
            {"name": "清完当前体力就结束", "pipeline_override": {"清体力_不足策略": {"next": ["清体力_不足清完"]}}},
        ],
    }
    o["自动使用体力道具"] = {
        "type": "select",
        "description": "体力不够时，是否打开「补充体力」使用体力道具。<br>⚠️ 已做防呆：道具列表正中间是「钻石」（说明没有体力道具了）时一律点空白取消。但<b>无法保证脚本 100% 不出错</b>，存在误用钻石买体力的可能；开启即视为已知风险。",
        "default_case": "不使用",
        "cases": [
            {"name": "不使用", "pipeline_override": {"清体力_补充入口": {"next": ["清体力_不足分流"]}}},
            {"name": "使用（已知风险）", "pipeline_override": {"清体力_补充入口": {"next": ["清体力_补_打开", "清体力_不足分流"]}}},
        ],
    }
    return o


if __name__ == "__main__":
    out = ROOT / "assets/resource/pipeline/sweep.json"
    out.write_text(json.dumps(build(), ensure_ascii=False, indent=4) + "\n", encoding="utf-8")
    task = {
        "task": [{
            "name": "🍰清体力",
            "entry": "清体力",
            "default_check": False,
            "description": "练习 → 所选关卡 → 刷到至少 60 / 120 体力 → 回任务页确认「累计消耗60点体力」。<br>默认用超强助力符快速过关；不够刷满时按「体力不足时」处理；默认不使用体力道具，绝不花钻石买体力。",
            "option": ["清体力关卡", "清体力难度", "道具符", "体力档", "体力不足时", "自动使用体力道具"],
        }],
        "option": options(),
    }
    (ROOT / "assets/tasks/Sweep.json").write_text(json.dumps(task, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")
    print("written sweep.json / Sweep.json, MAX_N =", MAX_N)
