"""MaaSH 测试包：按「套件」文件依次切账号、跑任务，跑完自动出报告。

用法（Windows，在 F:\\MaaSH\\testpack 里）：
    跑测试包.bat                      # 跑默认套件 suites\\标准.json
    跑测试包.bat suites\\快速.json     # 指定套件
    python run_suite.py --list        # 列出 MaaSH 里所有任务和选项名

不经过 MaaSH 界面：直接用 MaaFramework 加载 MaaSH 的 resource 和 interface.json，
选项的覆盖规则和 MaaSH 一样（任务自带 pipeline_override + 选中选项的 pipeline_override）。
运行前请先关掉 MaaSH（两边同时控制模拟器会互相抢）。

套件文件格式见 suites\\标准.json；账号写在 accounts.json（只在本机，不进仓库）。
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent


# ---------------------------------------------------------------- interface / 选项

def load_json(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as e:
        raise SystemExit(f"{p.name} 格式不对（第 {e.lineno} 行第 {e.colno} 个字附近）：{e.msg}。"
                         f"常见原因：两行之间少了英文逗号「,」，或用了中文引号。") from None


class Interface:
    """读 interface.json（含 import 的 tasks/*.json），把「任务 + 选项选择」翻译成 pipeline_override。"""

    def __init__(self, app: Path):
        self.app = app
        self.data = load_json(app / "interface.json")
        self.tasks: dict[str, dict] = {}
        self.options: dict[str, dict] = dict(self.data.get("option", {}))
        for t in self.data.get("task", []):
            self.tasks[t["name"]] = t
        for rel in self.data.get("import", []):
            d = load_json(app / rel)
            for t in d.get("task", []):
                self.tasks[t["name"]] = t
            self.options.update(d.get("option", {}))
        self.resource_options = []
        for r in self.data.get("resource", []):
            self.resource_options += r.get("option", [])
        self.global_options = self.data.get("global_option", [])

    def find_task(self, name: str) -> dict:
        if name in self.tasks:
            return self.tasks[name]
        # 允许省略 emoji、或写显示名（label）
        for t in self.tasks.values():
            plain = re.sub(r"^[^\w\u4e00-\u9fff]+", "", t["name"])
            if name in (plain, t.get("label"), re.sub(r"^[^\w\u4e00-\u9fff]+", "", t.get("label", ""))):
                return t
        raise KeyError(f"找不到任务「{name}」（用 --list 看全部任务名）")

    # --- 选项 → override
    def _case_names(self, opt: dict) -> list[str]:
        return [c["name"] for c in opt.get("cases", [])]

    def option_override(self, name: str, chosen, out: dict):
        opt = self.options.get(name)
        if opt is None:
            raise KeyError(f"找不到选项「{name}」")
        typ = opt.get("type", "select")
        if typ == "input":
            vals = {}
            for inp in opt.get("inputs", []):
                vals[inp["name"]] = (inp.get("default", ""), inp.get("pipeline_type", "string"))
            if chosen is not None:
                if isinstance(chosen, dict):
                    for k, v in chosen.items():
                        vals[k] = (v, vals.get(k, ("", "string"))[1])
                else:  # 只有一个输入框时可以直接写值
                    k = next(iter(vals))
                    vals[k] = (chosen, vals[k][1])
            merge(out, substitute(opt.get("pipeline_override", {}), vals))
            return
        if typ == "checkbox":
            sel = chosen if chosen is not None else opt.get("default_case", [])
            if isinstance(sel, str):
                sel = [sel]
            for c in opt.get("cases", []):
                if c["name"] in sel:
                    merge(out, c.get("pipeline_override", {}))
                    for sub in c.get("option", []):
                        self.option_override(sub, None, out)
            bad = set(sel) - set(self._case_names(opt))
            if bad:
                raise KeyError(f"选项「{name}」没有这些勾选项：{sorted(bad)}，可选：{self._case_names(opt)}")
            return
        # select / switch
        names = self._case_names(opt)
        sel = chosen if chosen is not None else opt.get("default_case", names[0] if names else None)
        if isinstance(sel, bool):
            sel = "Yes" if sel else "No"
        case = next((c for c in opt.get("cases", []) if c["name"] == sel), None)
        if case is None:
            raise KeyError(f"选项「{name}」没有「{sel}」，可选：{names}")
        merge(out, case.get("pipeline_override", {}))
        for sub in case.get("option", []):
            self.option_override(sub, self._pending.get(sub), out)

    def build(self, task_name: str, choices: dict, resource_choices: dict) -> tuple[str, dict]:
        t = self.find_task(task_name)
        self._pending = {**resource_choices, **choices}
        out: dict = {}
        for o in self.resource_options + self.global_options:
            self.option_override(o, resource_choices.get(o), out)
        merge(out, t.get("pipeline_override", {}))
        for o in t.get("option", []):
            self.option_override(o, choices.get(o), out)
        unknown = set(choices) - set(t.get("option", [])) - set(self._sub_options(t))
        if unknown:
            raise KeyError(f"任务「{t['name']}」没有选项 {sorted(unknown)}，它的选项：{t.get('option', [])}")
        return t["entry"], out

    def _sub_options(self, t: dict) -> list[str]:
        subs = []
        for o in t.get("option", []):
            for c in self.options.get(o, {}).get("cases", []):
                subs += c.get("option", [])
        return subs


def merge(dst: dict, src: dict):
    """和 MaaFW 的 pipeline_override 一样：按节点合并，节点里同名字段后者覆盖前者。"""
    for node, fields in src.items():
        if isinstance(fields, dict) and isinstance(dst.get(node), dict):
            dst[node].update(copy.deepcopy(fields))
        else:
            dst[node] = copy.deepcopy(fields)


def substitute(obj, vals: dict):
    if isinstance(obj, dict):
        return {k: substitute(v, vals) for k, v in obj.items()}
    if isinstance(obj, list):
        return [substitute(v, vals) for v in obj]
    if isinstance(obj, str):
        m = re.fullmatch(r"\{(.+?)\}", obj)
        if m and m.group(1) in vals:
            v, typ = vals[m.group(1)]
            if typ == "int":
                return int(v)
            if typ == "bool":
                return str(v).lower() in ("1", "true", "yes")
            return str(v)
        for k, (v, _) in vals.items():
            obj = obj.replace("{" + k + "}", str(v))
        return obj
    return obj


# ---------------------------------------------------------------- 运行记录

class Recorder:
    """收 MaaFW 的节点通知：每个节点的时间、颜色提示（focus）。"""

    def __init__(self):
        self.events: list[tuple[float, str, str, str]] = []  # (t, msg, node, focus)

    def make_sink(self):
        from maa.context import ContextEventSink

        rec = self

        class Sink(ContextEventSink):
            def on_raw_notification(self, context, msg, details):
                if not msg.startswith("Node.PipelineNode.") and not msg.startswith("Node.Action."):
                    return
                name = details.get("name", "")
                focus = details.get("focus")
                text = ""
                if isinstance(focus, dict):
                    key = msg.replace("Node.PipelineNode.", "Node.Action.")
                    text = focus.get(key) or focus.get(msg) or ""
                rec.events.append((time.time(), msg, name, text if isinstance(text, str) else json.dumps(text, ensure_ascii=False)))

        return Sink()

    def clear(self):
        self.events.clear()


TASK_PAGE_NODES = {"公共_打开任务页"}
BAD_NODES = {"公共_任务失败": "任务失败", "公共_退出后重开": "关游戏重开"}


def analyse(events, nodes):
    names = [n for _, msg, n, _ in events if msg == "Node.PipelineNode.Succeeded"]
    if not names:
        names = nodes
    colors = []
    for _, msg, n, text in events:
        if text:
            c = re.match(r"\[color:(\w+)\]", text or "")
            colors.append(((c.group(1) if c else ""), re.sub(r"\[/?color[^\]]*\]", "", text)))
    seen = set()
    colors_u = []
    for c in colors:
        if c not in seen:
            seen.add(c)
            colors_u.append(c)
    return {
        "nodes": len(names),
        "task_page": sum(1 for n in names if n in TASK_PAGE_NODES),
        "back": sum(1 for n in names if n == "公共_返回按钮"),
        "bad": [BAD_NODES[n] for n in names if n in BAD_NODES],
        "last": names[-1] if names else "",
        "messages": colors_u,
    }


# ---------------------------------------------------------------- 主流程

def find_adb_config(app: Path) -> dict:
    """从 MaaSH（MFA）配置里找当前用的模拟器连接参数。"""
    cfg_dir = app / "config" / "instances"
    best = None
    for f in sorted(cfg_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            d = load_json(f)
        except Exception:
            continue
        adb = d.get("AdbDevice")
        if adb and adb.get("AdbSerial"):
            best = adb
            break
    if not best:
        raise SystemExit("没在 MaaSH 配置里找到模拟器连接信息：请先在 MaaSH 里连上一次模拟器，或在 settings.json 里填 adb")
    return {
        "adb_path": best["AdbPath"],
        "address": best["AdbSerial"],
        "screencap_methods": int(best.get("ScreencapMethods", 0)) or None,
        "input_methods": int(best.get("InputMethods", 0)) or None,
        "config": json.loads(best.get("Config") or "{}"),
    }


def connect(app: Path, settings: dict):
    from maa.controller import AdbController

    adb = {**find_adb_config(app), **settings.get("adb", {})}
    kw = dict(adb_path=adb["adb_path"], address=adb["address"], config=adb.get("config") or {})
    if adb.get("screencap_methods"):
        kw["screencap_methods"] = adb["screencap_methods"]
    if adb.get("input_methods"):
        kw["input_methods"] = adb["input_methods"] & 0xFFFFFFFFFFFFFFFF
    agent = app / "libs" / "MaaAgentBinary"
    if not agent.exists():
        agent = app / "MaaAgentBinary"
    if agent.exists():
        kw["agent_path"] = str(agent)
    ctrl = AdbController(**kw)
    if not ctrl.post_connection().wait().succeeded:
        raise SystemExit(f"连不上模拟器 {adb['address']}：确认 MuMu 已开、MaaSH 已关")
    return ctrl, adb["address"]


def sim_controller(image: str):
    import cv2
    from maa.controller import CustomController

    img = cv2.imread(image)

    class Sim(CustomController):
        def connect(self): return True
        def request_uuid(self): return "sim"
        def start_app(self, i): return True
        def stop_app(self, i): return True
        def screencap(self): return img
        def click(self, x, y): return True
        def swipe(self, *a): return True
        def touch_down(self, *a): return True
        def touch_move(self, *a): return True
        def touch_up(self, *a): return True
        def click_key(self, k): return True
        def input_text(self, t): return True
        def key_down(self, k): return True
        def key_up(self, k): return True

    c = Sim()
    c.post_connection().wait()
    return c, "sim"


def save_image(img, path: Path):
    try:
        import cv2  # noqa

        cv2.imwrite(str(path), img)
        return True
    except Exception:
        pass
    try:
        from PIL import Image

        Image.fromarray(img[:, :, ::-1]).save(path)
        return True
    except Exception:
        return False


def expand_rounds(suite: dict, accounts: dict, check: bool = False) -> list[dict]:
    rounds = []
    for r in suite["rounds"]:
        r = copy.deepcopy(r)
        steps = []
        acc = r.get("account")
        if acc:
            if acc not in accounts and check:
                accounts = {**accounts, acc: f"<{acc}>"}
            if acc not in accounts:
                raise SystemExit(f"accounts.json 里没有「{acc}」：请先在 accounts.json 里填上历史账号列表里显示的文字")
            steps.append({"task": "✈️启动绘旅人", "option": {"使用指定账号登录": "Yes", "登录账号": {"账号": accounts[acc]}}, "label": f"切换到{acc}"})
        steps += [s if isinstance(s, dict) else {"task": s} for s in r["steps"]]
        r["steps"] = steps
        rounds.append(r)
    return rounds


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("suite", nargs="?", default=str(HERE / "suites" / "标准.json"))
    ap.add_argument("--app", default=None, help="MaaSH 安装目录（默认 testpack 的上一级里的 app）")
    ap.add_argument("--list", action="store_true", help="列出所有任务和它们的选项")
    ap.add_argument("--check", action="store_true", help="只检查套件写得对不对，不连模拟器")
    ap.add_argument("--only", default=None, help="只跑名字里含这段文字的轮次")
    ap.add_argument("--sim", default=None, help=argparse.SUPPRESS)  # 开发用：用一张静态截图代替模拟器
    args = ap.parse_args()

    settings = load_json(HERE / "settings.json") if (HERE / "settings.json").exists() else {}
    app = Path(args.app or settings.get("app") or (HERE.parent / "app")).resolve()
    itf = Interface(app)

    if args.list:
        for t in itf.tasks.values():
            print(f"{t['name']}  (显示名 {t.get('label', t['name'])})")
            for o in t.get("option", []):
                opt = itf.options.get(o, {})
                cases = [c["name"] for c in opt.get("cases", [])] or [i["name"] for i in opt.get("inputs", [])]
                print(f"    - {o} [{opt.get('type', 'select')}]: {cases}")
        print("共用设置（resource 选项）：", itf.resource_options)
        return

    suite_path = Path(args.suite)
    if not suite_path.is_absolute() and not suite_path.exists():
        suite_path = HERE / suite_path
    suite = load_json(suite_path)
    accounts = load_json(HERE / "accounts.json") if (HERE / "accounts.json").exists() else {}
    rounds = expand_rounds(suite, accounts, args.check)
    if args.only:
        rounds = [r for r in rounds if args.only in r["name"]]
    res_choices = suite.get("共用设置", {})

    plan = []
    for r in rounds:
        for s in r["steps"]:
            entry, ov = itf.build(s["task"], s.get("option", {}), res_choices)
            plan.append((r, s, entry, ov))
    print(f"套件「{suite.get('name', suite_path.stem)}」：{len(rounds)} 轮、{len(plan)} 步，选项检查通过")
    if args.check:
        for r, s, entry, ov in plan:
            print(f"  [{r['name']}] {s.get('label') or s['task']} → 入口 {entry}，覆盖 {len(ov)} 个节点")
        return

    from maa.resource import Resource
    from maa.tasker import Tasker
    from maa.toolkit import Toolkit

    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    out = Path(settings.get("report_dir") or (HERE.parent / "testreports")) / f"{stamp}_{suite_path.stem}"
    (out / "shots").mkdir(parents=True, exist_ok=True)
    (out / "config").mkdir(exist_ok=True)
    (out / "config" / "maa_option.json").write_text(json.dumps({"logging": True, "save_draw": False, "save_on_error": True, "stdout_level": 2}), encoding="utf-8")
    Toolkit.init_option(str(out))

    ctrl, addr = sim_controller(args.sim) if args.sim else connect(app, settings)
    res = Resource()
    if not res.post_bundle(str(app / "resource")).wait().succeeded:
        raise SystemExit("加载 resource 失败")
    tasker = Tasker()
    tasker.bind(res, ctrl)
    rec = Recorder()
    tasker.add_context_sink(rec.make_sink())
    print(f"已连接 {addr}，报告目录 {out}")

    results = []
    t_all = time.time()
    for i, (r, s, entry, ov) in enumerate(plan, 1):
        label = s.get("label") or s["task"]
        print(f"[{i}/{len(plan)}] {r['name']} · {label} …", flush=True)
        rec.clear()
        t0 = time.time()
        job = tasker.post_task(entry, ov).wait()
        detail = job.get()
        dur = time.time() - t0
        nodes = [n.name for n in detail.nodes] if detail else []
        a = analyse(rec.events, nodes)
        ok = job.succeeded
        budget = s.get("最长秒数") or suite.get("最长秒数", {}).get(re.sub(r"^[^\w\u4e00-\u9fff]+", "", s["task"]))
        problems = []
        if not ok:
            problems.append(f"任务失败（停在 {a['last']}）")
        problems += a["bad"]
        if budget and dur > budget:
            problems.append(f"耗时 {dur:.0f}s 超过预期 {budget}s")
        for want in s.get("必须经过", []):
            if want not in nodes:
                problems.append(f"没经过 {want}")
        for bad in s.get("不能经过", []):
            if bad in nodes:
                problems.append(f"不该经过 {bad}")
        shot = out / "shots" / f"{i:02d}_{re.sub(r'[^\w\u4e00-\u9fff]', '', label)}.png"
        img = ctrl.post_screencap().wait().get()
        has_shot = img is not None and save_image(img, shot)
        (out / f"{i:02d}_trace.txt").write_text(
            "\n".join(f"{dt.datetime.fromtimestamp(t).strftime('%H:%M:%S.%f')[:-3]} {msg.split('.')[-1]:<10} {n} {txt}" for t, msg, n, txt in rec.events),
            encoding="utf-8")
        results.append({
            "i": i, "round": r["name"], "task": label, "ok": ok and not problems, "succeeded": ok, "sec": round(dur, 1),
            "task_page": a["task_page"], "back": a["back"], "nodes": a["nodes"], "last": a["last"],
            "problems": problems, "messages": a["messages"], "shot": shot.name if has_shot else "",
        })
        mark = "✅" if results[-1]["ok"] else "❌"
        print(f"    {mark} {dur:.0f}s  任务页 {a['task_page']} 次  返回键 {a['back']} 次  {'；'.join(problems)}", flush=True)
        if not ok and s.get("失败就停", suite.get("失败就停", False)):
            print("失败就停：后面的不跑了")
            break

    total = time.time() - t_all
    write_report(out, suite, suite_path, results, total, addr)
    print(f"\n跑完了：{sum(r['ok'] for r in results)}/{len(results)} 通过，共 {total / 60:.1f} 分钟")
    print(f"报告：{out / '报告.md'}")


def write_report(out: Path, suite, suite_path, results, total, addr):
    (out / "结果.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    L = [f"# MaaSH 测试报告：{suite.get('name', suite_path.stem)}", "",
         f"- 时间：{out.name[:15]}　模拟器：{addr}　总耗时：{total / 60:.1f} 分钟",
         f"- 通过：**{sum(r['ok'] for r in results)} / {len(results)}**", "",
         "| # | 轮次 | 任务 | 结果 | 耗时 | 任务页 | 返回键 | 问题 |", "|---|---|---|---|---|---|---|---|"]
    for r in results:
        L.append(f"| {r['i']} | {r['round']} | {r['task']} | {'✅' if r['ok'] else '❌'} | {r['sec']}s | {r['task_page']} | {r['back']} | {'；'.join(r['problems'])} |")
    L += ["", "## 每步的提示信息", ""]
    for r in results:
        msgs = [f"{'🟧' if c == 'Orange' else '🟩' if c == 'Limegreen' else '▫️'} {t}" for c, t in r["messages"]]
        L.append(f"**{r['i']}. {r['task']}**（{r['round']}）：" + ("　".join(msgs) if msgs else "无"))
    L += ["", "每一步的节点流水在 `NN_trace.txt`，结束时的画面在 `shots/`，失败截图在 `debug/on_error/`，完整日志 `debug/maafw.log`。",
          "有问题时把整个报告文件夹发给 Claude。"]
    (out / "报告.md").write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
