"""
⚠️ 已过时：cinema.json 生成后又手工修过很多处（弹窗处理、扫荡完成判断等），
直接重新生成会把这些修复冲掉。现在请直接改 assets/resource/pipeline/cinema.json。
生成「时光电影院扫荡 + 电影院商店兑换」节点和任务定义。
  python tools/gen_cinema.py
输出：assets/resource/pipeline/cinema.json、assets/tasks/Cinema.json
"""
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
CHARS = ["艾因", "路辰", "罗夏", "司岚", "叶瑄"]  # 拼音顺序
# 显示名, OCR 正则
ITEMS = [
    ("觉悟", "^觉悟$"), ("梦境之羽", "梦境之羽"),
    ("高级技能包*5", "高级技能包"), ("高级突破包*5", "高级突破包"),
    ("中级技能包*5", "中级技能包"), ("中级突破包*5", "中级突破包"),
    ("初级技能包*5", "初级技能包"), ("初级突破包*5", "初级突破包"),
    ("星尘之铃·承", "星尘之铃.?承"), ("记忆铭刻·影", "记忆铭刻.?影"),
] + [(f"帝国训练·{c}", f"帝国训练.?{c}") for c in CHARS]
SLOTS = 8
FAIL = ["公共_任务失败"]
POP = ["[JumpBack]公共_获得奖励", "[JumpBack]公共_点击空白继续"]
W = {"time": 800, "timeout": 10000}


def O(t, roi):
    return {"type": "OCR", "param": {"expected": t, "roi": roi}}


def R(x):
    return {"recognition": x}


def lg(c, t, k="Node.Action.Succeeded"):
    return {k: f"[color:{c}]{t}[/color]"}


def after(n):
    """第 n 顺位之后：依次尝试后面所有（启用的）顺位，最后到完成"""
    return [f"兑换_第{k}顺位" for k in range(n + 1, SLOTS + 1)] + ["Flag_兑换完成"]


def build(home):
    d = {}
    # ---------------- 扫荡 ----------------
    d["电影院"] = {"desc": "任务入口：主界面「练习」→ 时光电影院，按拼音顺序给 5 个角色各扫荡一次（每周一次）",
                 "timeout": 60000, "next": ["电影院_打开练习", "[JumpBack]公共_返回主界面"], "on_error": FAIL,
                 "focus": lg("Dimgray", "开始：时光电影院", "Node.Action.Starting")}
    d["电影院_打开练习"] = {"desc": "主界面「练习」（全景在底部，默认主题在右侧）",
                       "recognition": {"type": "And", "param": {"all_of": [R(home), R({"type": "Or", "param": {"any_of": [
                           R(O("练习", [950, 640, 90, 55])), R(O("^练习$", [1005, 410, 110, 70]))]}})], "box_index": 1}},
                       "action": {"type": "Click"}, "post_wait_freezes": W, "next": ["电影院_进入"], "on_error": FAIL}
    d["电影院_进入"] = {"desc": "日常练习页「时光电影院」", "recognition": O("时光电影院", [180, 420, 240, 70]),
                    "action": {"type": "Click"}, "post_wait_freezes": {"time": 1000, "timeout": 15000}, "timeout": 15000,
                    "next": [f"电影院_换人_{CHARS[0]}"], "on_error": FAIL}
    active = {"type": "And", "param": {"all_of": [R(O("扫\\s*荡", [690, 520, 140, 55])), R({"type": "ColorMatch", "param": {
        "roi": [700, 530, 170, 40], "method": 4, "lower": [222, 222, 230], "upper": [255, 255, 255], "count": 2500}})]}}
    grey = {"type": "And", "param": {"all_of": [R(O("扫\\s*荡", [690, 520, 140, 55])), R({"type": "ColorMatch", "param": {
        "roi": [700, 530, 170, 40], "method": 4, "lower": [130, 130, 130], "upper": [185, 185, 190], "count": 2500}})]}}
    for i, c in enumerate(CHARS):
        nxt = f"电影院_换人_{CHARS[i + 1]}" if i + 1 < len(CHARS) else "Flag_电影院扫荡完成"
        d[f"电影院_换人_{c}"] = {"desc": f"左下角当前角色按钮（名字 + ⇆），打开角色列表",
                              "recognition": O("时光电影院", [90, 15, 200, 55]),
                              "action": {"type": "Click", "param": {"target": [25, 553, 120, 42]}},
                              "post_wait_freezes": W, "next": [f"电影院_选_{c}"]}
        d[f"电影院_选_{c}"] = {"desc": f"角色列表里点「{c}」", "recognition": O(f"^{c[0]}\\s*{c[1]}$", [10, 250, 160, 300]),
                            "action": {"type": "Click"}, "post_wait_freezes": {"time": 1000, "timeout": 10000},
                            "timeout": 10000, "next": [f"电影院_{c}"], "on_error": [nxt]}
        d[f"电影院_{c}"] = {"desc": f"{c}：扫荡按钮可点就扫荡，灰色就是本周已扫荡", "timeout": 60000,
                         "next": ["[JumpBack]电影院_扫荡", f"电影院_{c}_已完成"], "on_error": [nxt]}
        d[f"电影院_{c}_已完成"] = {"recognition": grey, "next": [nxt],
                               "focus": lg("Dimgray", f"{c}：本周已扫荡")}
    d["电影院_扫荡"] = {"desc": "扫荡按钮为亮色（可扫荡）", "recognition": active, "action": {"type": "Click"},
                     "max_hit": 6, "post_wait_freezes": W, "next": ["电影院_确认扫荡"]}
    d["电影院_确认扫荡"] = {"desc": "「每周仅可扫荡一次…是否开始扫荡？」→ 确定",
                       "recognition": {"type": "And", "param": {"all_of": [R(O("扫荡", [560, 190, 160, 70])), R(O("确\\s*定", [750, 435, 130, 60]))], "box_index": 1}},
                       "action": {"type": "Click"}, "post_wait_freezes": {"time": 1500, "timeout": 20000}, "timeout": 10000,
                       "next": ["电影院_扫荡结果"]}
    d["电影院_扫荡结果"] = {"timeout": 30000,
                       "next": ["[JumpBack]电影院_不再处理"] + POP + ["电影院_扫荡完成"]}
    d["电影院_不再处理"] = {"desc": "随机事件一律「不再处理」", "recognition": O("不再处理", [380, 530, 200, 55]),
                       "action": {"type": "Click"}, "post_wait_freezes": W, "max_hit": 6}
    # 扫完后列表会滚到下一场，扫荡按钮位置会变：在右侧整列找最下面的「扫荡」，再看它是不是灰的
    d["电影院_扫荡完成"] = {"desc": "扫完后列表会滚到下一场，扫荡按钮位置会变：在右侧整列找最下面的「扫荡」",
                       "recognition": {"type": "OCR", "param": {"expected": "^扫\\s*荡$", "roi": [620, 60, 280, 640],
                                                                "order_by": "Vertical", "index": -1}},
                       "next": ["电影院_扫荡已灰"]}
    d["电影院_扫荡已灰"] = {"recognition": {"type": "ColorMatch", "param": {"roi": "电影院_扫荡完成", "roi_offset": [-55, -8, 110, 16],
                                                                      "method": 4, "lower": [130, 130, 130], "upper": [185, 185, 190], "count": 2000}},
                       "focus": lg("Dimgray", "扫荡完成")}
    d["Flag_电影院扫荡完成"] = {"desc": "5 个角色都已检查；开了兑换就继续去商店", "next": ["兑换", "电影院_结束"],
                           "focus": lg("Limegreen", "时光电影院：本周扫荡已完成")}

    d["电影院_结束"] = {"desc": "未开启商店兑换"}
    # ---------------- 商店兑换（可选） ----------------
    d["兑换"] = {"desc": "子功能「自动兑换商店材料」入口；关闭时直接结束", "enabled": False,
               "timeout": 60000, "next": ["兑换_打开采购", "[JumpBack]公共_返回主界面"], "on_error": FAIL,
               "focus": lg("Dimgray", "开始：电影院商店兑换", "Node.Action.Starting")}
    d["兑换_打开采购"] = {"recognition": {"type": "And", "param": {"all_of": [R(home), R(O("^采购$", [300, 480, 960, 130]))], "box_index": 1}},
                      "action": {"type": "Click"}, "post_wait_freezes": W, "next": ["兑换_兑换页"], "on_error": FAIL}
    d["兑换_兑换页"] = {"desc": "左侧「兑换」", "recognition": O("^兑换$", [25, 435, 100, 65]), "action": {"type": "Click"},
                     "post_wait_freezes": W, "timeout": 15000, "next": ["兑换_电影院页"], "on_error": FAIL}
    d["兑换_电影院页"] = {"desc": "上方「电影院」页签", "recognition": O("^电影院$", [600, 70, 300, 60]), "action": {"type": "Click"},
                      "post_wait_freezes": W, "timeout": 15000, "next": after(0), "on_error": FAIL}
    tab = O("^电影院$", [600, 70, 300, 60])
    d["兑换_下滚"] = {"recognition": tab, "action": {"type": "Swipe", "param": {"begin": [700, 560, 20, 20], "end": [700, 250, 20, 20], "duration": 400}},
                   "max_hit": 4 * SLOTS, "post_wait_freezes": {"time": 600, "timeout": 5000}}
    for n in range(1, SLOTS + 1):
        nxt = after(n)
        d[f"兑换_第{n}顺位"] = {"desc": f"第 {n} 顺位：回到列表顶部，开始找商品（由选项决定买什么，「不购买」时跳过）",
                             "enabled": False, "recognition": tab,
                             "action": {"type": "Swipe", "param": {"begin": [700, 220, 20, 20], "end": [700, 640, 20, 20], "duration": 300}},
                             "repeat": 3, "repeat_delay": 200, "post_wait_freezes": {"time": 600, "timeout": 5000},
                             "next": [f"兑换_第{n}_找"]}
        d[f"兑换_第{n}_找"] = {"timeout": 30000, "next": [f"兑换_第{n}_商品", "[JumpBack]兑换_下滚"], "on_error": nxt}
        d[f"兑换_第{n}_商品"] = {"desc": "在商品列表里找到商品名并点开（名字由选项改写）", "recognition": O("^觉悟$", [160, 130, 1040, 580]),
                              "action": {"type": "Click"}, "post_wait_freezes": W, "next": [f"兑换_第{n}_最大数量", f"兑换_第{n}_点价格"],
                              "on_error": nxt, "timeout": 5000}
        d[f"兑换_第{n}_最大数量"] = {"desc": "有数量选择时点最右边的 max 按钮",
                                "recognition": {"type": "And", "param": {"all_of": [R(O("商品内容", [470, 250, 140, 45])), R(O("^\\d+$", [600, 460, 150, 50]))]}},
                                "action": {"type": "Click", "param": {"target": [895, 460, 95, 48]}},
                                "post_wait_freezes": {"time": 500, "timeout": 5000}, "next": [f"兑换_第{n}_点价格"]}
        d[f"兑换_第{n}_点价格"] = {"desc": "点下方的价格按钮（电影票）",
                               "recognition": {"type": "And", "param": {"all_of": [R(O("商品内容", [470, 250, 140, 45])), R(O("^\\d+$", [580, 540, 170, 50]))], "box_index": 1}},
                               "action": {"type": "Click"}, "post_wait_freezes": {"time": 1000, "timeout": 8000}, "next": [f"兑换_第{n}_结果"]}
        d[f"兑换_第{n}_结果"] = {"timeout": 6000, "next": ["[JumpBack]公共_付费防呆", f"兑换_第{n}_成功"], "on_error": ["兑换_票不足"]}
        d[f"兑换_第{n}_成功"] = {"recognition": O("恭喜获得|获得奖励", [380, 130, 520, 140]),
                              "action": {"type": "Click", "param": {"target": [560, 630, 160, 30]}},
                              "post_wait_freezes": W, "next": nxt, "focus": lg("Deepskyblue", f"第 {n} 顺位兑换成功")}
    d["兑换_票不足"] = {"desc": "点了价格但没有获得奖励：视为电影票不足，关掉弹窗并停止兑换",
                     "action": {"type": "Click", "param": {"target": [20, 660, 40, 40]}}, "post_wait_freezes": W,
                     "focus": lg("Orange", "电影票不足或无法兑换，已停止兑换")}
    d["Flag_兑换完成"] = {"focus": lg("Limegreen", "电影院商店兑换完成")}
    return d


def task():
    cases_item = [{"name": "不购买", "pipeline_override": {}}]
    opts = {"自动兑换商店材料": {"type": "switch", "description": "扫荡后去「采购 → 兑换 → 电影院」，按顺位从上到下兑换，直到电影票用完",
                            "cases": [{"name": "No", "pipeline_override": {"兑换": {"enabled": False}}},
                                      {"name": "Yes", "pipeline_override": {"兑换": {"enabled": True}},
                                       "option": [f"第{n}顺位" for n in range(1, SLOTS + 1)]}]}}
    for n in range(1, SLOTS + 1):
        cases = [{"name": "不购买", "pipeline_override": {f"兑换_第{n}顺位": {"enabled": False}}}]
        for name, rx in ITEMS:
            cases.append({"name": name, "pipeline_override": {
                f"兑换_第{n}顺位": {"enabled": True},
                f"兑换_第{n}_商品": {"recognition": O(rx, [160, 130, 1040, 580])}}})
        opts[f"第{n}顺位"] = {"type": "select", "label": f"兑换第 {n} 顺位", "default_case": "不购买", "cases": cases}
    return {"task": [{"name": "🎬时光电影院", "entry": "电影院", "default_check": False,
                      "description": "每周：练习 → 时光电影院，5 个角色各扫荡一次，随机事件一律「不再处理」。<br>可选：扫荡后按顺位兑换电影院商店材料，直到电影票用完。",
                      "option": ["自动兑换商店材料"]}], "option": opts}


if __name__ == "__main__":
    home = json.loads((ROOT / "assets/resource/pipeline/common.json").read_text(encoding="utf-8"))["Flag_在主界面"]["recognition"]
    (ROOT / "assets/resource/pipeline/cinema.json").write_text(json.dumps(build(home), ensure_ascii=False, indent=4) + "\n", encoding="utf-8")
    (ROOT / "assets/tasks/Cinema.json").write_text(json.dumps(task(), ensure_ascii=False, indent=4) + "\n", encoding="utf-8")
    print("ok")
