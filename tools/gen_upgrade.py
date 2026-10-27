"""生成「画灵提升」「绘卷提升」节点 → assets/resource/pipeline/upgrade.json

任务页「前往」→ 图鉴（画灵/绘卷页签）→ 点列表第一张 → 详情页：
  有「培养」→ 点培养（游戏自动把目标设为 +1 级）→「提升」是深色才点 → 等级提升弹窗 → 回任务页复核
  「等级已满 / 突破」→ 点右侧箭头换下一张，直到出现等级未满的
运行：python tools/gen_upgrade.py
"""
import json
from pathlib import Path

KINDS = [("画灵", "画灵提升"), ("绘卷", "绘卷提升")]
FREEZE = {"time": 500, "timeout": 1500, "rate_limit": 200}
LV_BTN = [1040, 200, 130, 55]          # 等级那一行右侧按钮：+培养 / 等级已满
UP_BTN = [1015, 390, 150, 60]          # 「提升」
DARK = {"lower": [40, 30, 20], "upper": [115, 100, 90], "count": 1500}


def ocr(e, roi):
    return {"recognition": {"type": "OCR", "param": {"expected": e, "roi": roi}}}


def build():
    d = {}
    for k, task in KINDS:
        d[f"{k}_流程"] = {
            "desc": f"在图鉴「{k}」列表：点第一张（从上到下、从左到右），进详情页后找等级未满的",
            "timeout": 20000,
            "next": [f"{k}_点第一张", "[JumpBack]公共_获得奖励", "[JumpBack]公共_跳过卡面", "[JumpBack]公共_点击空白继续"],
            "on_error": ["公共_任务失败"],
        }
        d[f"{k}_点第一张"] = {
            "recognition": {"type": "OCR", "param": {"expected": "图鉴", "roi": [114, 17, 152, 66], "only_rec": True}},
            "desc": "10-27 实机：刚进图鉴、列表还在动时就点，点击被吞，停在列表干等 8 秒失败 → 点前先等列表静止；进不去详情就再点（最多 3 次）",
            "action": {"type": "Click", "param": {"target": [150, 175, 115, 110]}},
            "max_hit": 3,
            "pre_wait_freezes": {"time": 800, "target": [120, 150, 1060, 450], "timeout": 4000, "rate_limit": 200},
            "post_wait_freezes": FREEZE,
            "next": [f"{k}_详情"],
        }
        d[f"{k}_详情"] = {
            "desc": "详情页：有「培养」就升级，「等级已满/突破」就点右箭头换下一张",
            "timeout": 8000,
            "next": [f"{k}_培养", f"{k}_下一张", f"{k}_需突破", f"{k}_点第一张"],
            "on_error": ["公共_任务失败"],
        }
        d[f"{k}_培养"] = {
            "recognition": ocr("培\\s*养", LV_BTN)["recognition"],
            "action": {"type": "Click"},
            "max_hit": 3,
            "post_wait_freezes": FREEZE,
            "timeout": 5000,
            "next": [f"{k}_提升", f"{k}_材料不足", f"{k}_需突破"],
            "on_error": ["公共_任务失败"],
        }
        d[f"{k}_下一张"] = {
            "desc": f"这张{k}等级已满（或要突破）：点右侧箭头看下一张。很可能要翻很多张，所以任务说明里建议收藏等级未满的{k}",
            "recognition": ocr("等级已满|突\\s*破", LV_BTN)["recognition"],
            "action": {"type": "Click", "param": {"target": [1215, 335, 45, 50]}},
            "max_hit": 300,
            "post_wait_freezes": FREEZE,
            "next": [f"{k}_详情"],
        }
        d[f"{k}_需突破"] = {
            "desc": f"10-27 实机：等级到了当前阶段的上限（如「三阶画灵等级上限为70级」）时，等级那一行仍显示「+培养」，点了之后变成「突破后等级上限可提升至…」和「突破」按钮——要突破才能再升，不在这里突破，点右侧箭头换下一张{k}",
            "recognition": ocr("突破后等级上限|^突\\s*破$", [540, 200, 640, 130])["recognition"],
            "action": {"type": "Click", "param": {"target": [1215, 335, 45, 50]}},
            "max_hit": 300,
            "post_wait_freezes": FREEZE,
            "next": [f"{k}_详情"],
            "focus": {"Node.Action.Starting": f"[color:Dimgray]这张{k}要突破才能再升，换下一张[/color]"},
        }
        d[f"{k}_提升"] = {
            "desc": "「提升」是深色（材料够）才点。只升 1 级：点培养时游戏已经自动把目标设为 +1，不再点「+」",
            "recognition": {"type": "And", "param": {"all_of": [
                ocr("^提\\s*升$", UP_BTN),
                {"recognition": {"type": "ColorMatch", "param": {"roi": UP_BTN, **DARK}}}], "box_index": 0}},
            "action": {"type": "Click"},
            "post_wait_freezes": FREEZE,
            "timeout": 5000,
            "next": [f"{k}_已提升", "[JumpBack]公共_获得奖励", "[JumpBack]公共_跳过卡面", "[JumpBack]公共_点击空白继续"],
            "on_error": ["公共_进入日常列表"],
        }
        d[f"{k}_已提升"] = {
            "desc": "弹出「等级提升」：点空白关掉，算完成（10-24 起不再回任务页复核）",
            "recognition": ocr("等级提升", [454, 187, 392, 126])["recognition"],
            "action": {"type": "Click", "param": {"target": [560, 650, 160, 40]}},
            "post_wait_freezes": FREEZE,
            "next": [f"{task}_完成"],
            "focus": {"Node.Action.Succeeded": f"[color:Dimgray]{k}已升 1 级[/color]"},
        }
        d[f"{task}_完成"] = {
            "desc": "10-24：弹出「等级提升」就算完成，不再回任务页复核",
            "focus": {"Node.Action.Succeeded": f"[color:Limegreen]{task}完成：已升 1 级[/color]"},
        }
        d[f"{k}_材料不足"] = {
            "desc": "「提升」是灰色：经验材料或金币不够",
            "recognition": ocr("提\\s*升", UP_BTN)["recognition"],
            "focus": {"Node.Action.Succeeded": f"[color:Orange]{k}升级材料不够（「提升」是灰色），跳过[/color]"},
        }
    return d


if __name__ == "__main__":
    out = Path(__file__).parent.parent / "assets/resource/pipeline/upgrade.json"
    out.write_text(json.dumps(build(), ensure_ascii=False, indent=4) + "\n", encoding="utf-8")
    print(f"written {out}")
