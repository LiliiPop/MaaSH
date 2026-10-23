"""生成「出行头像栏按发色认人」→ assets/resource/pipeline/avatar.json

头像栏展开后从左到右 5 个位置（顺序按好感度排，每个号不一样），头像会随装扮变，所以不认整张头像，
只看每个位置头顶那一小块头发的颜色：黑 = 艾因，深蓝紫 = 司岚，橙 = 罗夏，浅金 = 路辰，银蓝 = 叶瑄。
橙发的高光和金发很像，所以找路辰时先排除「这一格是橙发」。
数值来自两个号的截图（10-23 第二个号 on_error、10-15 outing/03_character）。
修改后运行：python tools/gen_avatar.py
"""
import json
from pathlib import Path

SLOT_X = [78, 175, 272, 368, 465]           # 5 个头像的中心 x
HAIR = lambda cx: [cx - 12, 620, 18, 16]     # 头顶头发那一小块
CLICK = lambda cx: [cx - 20, 630, 40, 40]
COLOR = {   # 角色: (lower, upper, count)
    "艾因": ([0, 0, 0], [100, 100, 105], 30),
    "司岚": ([60, 60, 125], [170, 170, 245], 200),
    "罗夏": ([228, 140, 0], [255, 212, 150], 25),
    "路辰": ([228, 222, 150], [255, 248, 222], 80),
    "叶瑄": ([180, 195, 232], [240, 250, 255], 150),
}
EXCLUDE = {"路辰": ["罗夏"]}
POPS = ["[JumpBack]公共_晚点再说", "[JumpBack]公共_稍后再说", "[JumpBack]公共_不再提醒", "[JumpBack]公共_我知道了"]
PW = {"time": 500, "timeout": 3000, "rate_limit": 200}
USES = {  # 前缀: (点中之后去哪, 一个都没认出时去哪, 点中之后一直卡住时去哪)
    "赠礼": (POPS + ["出行赠礼_打开赠礼"], "出行赠礼_没认出角色", "出行赠礼_跳过"),
    "收礼": (POPS + ["出行收礼_流程"], "出行收礼_没认出角色", "出行收礼_流程"),
}


def color(name, cx):
    lo, hi, n = COLOR[name]
    return {"type": "ColorMatch", "param": {"roi": HAIR(cx), "method": 4, "lower": lo, "upper": hi, "count": n}}


def build():
    d = {}
    for p, (after, fail, stuck) in USES.items():
        for c in COLOR:
            for k, cx in enumerate(SLOT_X, 1):
                nxt = f"{p}找人_{c}_{k + 1}" if k < len(SLOT_X) else fail
                d[f"{p}找人_{c}_{k}"] = {
                    "desc": f"{p}：看头像栏第 {k} 格是不是{c}",
                    "next": [f"{p}找人_{c}_{k}_不是{e}" for e in EXCLUDE.get(c, [])] + [f"{p}找人_{c}_{k}_点", nxt],
                }
                for e in EXCLUDE.get(c, []):
                    d[f"{p}找人_{c}_{k}_不是{e}"] = {"desc": f"这一格其实是{e}（发色相近），跳过", "recognition": color(e, cx), "next": [nxt]}
                d[f"{p}找人_{c}_{k}_点"] = {
                    "desc": f"第 {k} 格头发颜色是{c}：点这个头像（选中后头像栏会自动收起）",
                    "recognition": color(c, cx),
                    "action": {"type": "Click", "param": {"target": CLICK(cx)}},
                    "post_wait_freezes": PW,
                    "post_delay": 1500,  # 换人后角色有台词 / 动画，马上点「赠礼」常常没反应（10-24 实跑连续 3 次没打开）
                    "next": after,
                    "on_error": [stuck],  # 10-24：选中人后底栏「赠礼」一直认不出时整个任务失败了，改成跳过、最后在任务页确认
                    "focus": {"Node.Action.Succeeded": f"[color:Dimgray]{p}：头像栏第 {k} 格是{c}，已选中[/color]"},
                }
    return d


if __name__ == "__main__":
    out = Path(__file__).parent.parent / "assets/resource/pipeline/avatar.json"
    out.write_text(json.dumps(build(), ensure_ascii=False, indent=4) + "\n", encoding="utf-8")
    print("写入", out)
