"""生成「🔴清红点」→ assets/resource/pipeline/redpoint.json

主界面「活动」→ 活动中心：左侧活动列表从上往下看 8 个位置，带红点的点开，
页面里只点写着「领取」的按钮，以及「第 N 天」签到格里发光的那一格；弹窗按通用规则关掉。
绝不点「前往」「充值」「解锁」和任何 ¥ / 钻石价格（出现付费弹窗、支付窗口一律取消）。
修改后运行：python tools/gen_redpoint.py
"""
import json
from pathlib import Path

SLOTS = 8
ROW_Y = [135 + round(67.5 * i) for i in range(SLOTS)]   # 左侧活动名文字的中心 y
PW = {"time": 600, "timeout": 2500, "rate_limit": 200}
POPS = ["[JumpBack]公共_晚点再说", "[JumpBack]公共_生日弹窗等待", "[JumpBack]公共_稍后再说", "[JumpBack]公共_不再提醒", "[JumpBack]公共_我知道了"]
SAFE = ["[JumpBack]公共_放弃付款", "[JumpBack]公共_关闭支付", "[JumpBack]公共_付费防呆", "[JumpBack]公共_取消弹窗",
        "[JumpBack]兑换_关选择弹窗", "[JumpBack]公共_获得奖励", "[JumpBack]公共_点击空白继续"]


def main_guard():
    c = json.load(open(Path(__file__).parent.parent / "assets/resource/pipeline/common.json", encoding="utf-8"))
    return c["Flag_在主界面"]["recognition"]


def build():
    d = {}
    d["清红点"] = {
        "desc": "任务入口：主界面「活动」→ 活动中心，把带红点的活动看一遍，能领的领掉",
        "timeout": 60000,
        "next": POPS + ["红点_打开活动", "[JumpBack]公共_返回主界面"],
        "on_error": ["公共_任务失败"],
        "focus": {"Node.Action.Starting": "[color:Dimgray]开始：清红点（活动中心）[/color]"},
    }
    d["红点_打开活动"] = {
        "desc": "主界面上的「活动」（全景 / 出行主题在左侧竖排，默认主题在底栏）。必须先确认在主界面",
        "recognition": {"type": "And", "param": {"all_of": [
            {"recognition": main_guard()},
            {"recognition": {"type": "OCR", "param": {"expected": "^活动$", "roi": [0, 100, 1280, 620]}}}],
            "box_index": 1}},
        "action": {"type": "Click", "param": {"target_offset": [0, -15, 0, 0]}},
        "post_wait_freezes": PW, "max_hit": 3,
        "next": ["红点_活动中心"] + POPS,
        "on_error": ["公共_任务失败"], "timeout": 10000,
    }
    d["红点_活动中心"] = {
        "recognition": {"type": "OCR", "param": {"expected": "活动中心", "roi": [94, 12, 232, 76]}},
        "timeout": 15000, "next": ["红点_槽_1"], "on_error": ["公共_任务失败"],
    }
    for k, y in enumerate(ROW_Y, 1):
        nxt = f"红点_槽_{k + 1}" if k < SLOTS else "Flag_清红点完成"
        d[f"红点_槽_{k}"] = {"desc": f"活动列表第 {k} 个位置", "next": [f"红点_有红点_{k}", nxt]}
        d[f"红点_有红点_{k}"] = {
            "desc": "活动名右上角有红点 → 点开这个活动",
            "recognition": {"type": "ColorMatch", "param": {
                "roi": [222, y - 36, 32, 30], "method": 4, "lower": [200, 60, 45], "upper": [255, 135, 125], "count": 40}},
            "action": {"type": "Click", "param": {"target": [50, y - 18, 170, 36]}},
            "post_wait_freezes": PW,
            "next": [f"红点_扫描_{k}"],
        }
        d[f"红点_扫描_{k}"] = {
            "desc": "在这个活动页里找能领的东西；什么都没有就看下一个活动",
            "pre_wait_freezes": PW,
            "next": SAFE + POPS + [f"[JumpBack]红点_领取_{k}", f"[JumpBack]红点_发光_{k}", nxt],
        }
        d[f"红点_领取_{k}"] = {
            "desc": "只点写着「领取」的按钮（「前往」「充值」「未达成」都不点）",
            "recognition": {"type": "OCR", "param": {"expected": "^领\\s*取$", "roi": [640, 170, 630, 470]}},
            "action": {"type": "Click"}, "post_wait_freezes": PW, "max_hit": 6,
            "focus": {"Node.Action.Succeeded": "[color:Dimgray]活动中心：点了「领取」[/color]"},
        }
        d[f"红点_发光_{k}"] = {
            "desc": "「第 N 天」签到格里发光（金色外框）的那一格：点它领当天的奖励",
            "recognition": {"type": "And", "param": {"all_of": [
                {"recognition": {"type": "OCR", "param": {"expected": "^第.天$", "roi": [460, 360, 760, 50]}}},
                {"recognition": {"type": "ColorMatch", "param": {
                    "roi": [460, 400, 760, 120], "method": 4, "lower": [230, 190, 0], "upper": [255, 255, 120],
                    "count": 600, "connected": True}}}], "box_index": 1}},
            "action": {"type": "Click"}, "post_wait_freezes": PW, "max_hit": 2,
            "focus": {"Node.Action.Succeeded": "[color:Dimgray]活动中心：点了发光的签到格[/color]"},
        }
    d["Flag_清红点完成"] = {
        "desc": "活动列表都看过了",
        "focus": {"Node.Action.Succeeded": "[color:Limegreen]清红点完成：活动中心带红点的活动都看过了[/color]"},
        "next": ["公共_返回主界面"],
    }
    return d


if __name__ == "__main__":
    out = Path(__file__).parent.parent / "assets/resource/pipeline/redpoint.json"
    out.write_text(json.dumps(build(), ensure_ascii=False, indent=4) + "\n", encoding="utf-8")
    print("写入", out)
