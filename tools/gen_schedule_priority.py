"""生成「🗓️安排日程」的顺位选项（assets/tasks/Schedule.json 的 option 部分）。

界面上逐级选：先选第 1 顺位，选了谁，第 2 顺位的下拉里就不再出现他，依此类推；
选完第 4 顺位后，剩下那位自动当第 5 顺位。任何一级选「不指定」就到此为止。
这样用户没法把同一个男主填两次（第二次点名字会把他取消选中）。

用法：python3 tools/gen_schedule_priority.py
"""
import json
from collections import OrderedDict as OD
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MEN = ['罗夏', '司岚', '叶瑄', '艾因', '路辰']
OCR_ALIAS = {'艾因': '艾因|文因'}  # 实机 OCR 偶尔把「艾因」认成「文因」
DESC1 = ("日程两页都按顺位选男主（全部「不指定」= 两页都随机）。"
         "第一页（多人，选 5 人）：把名单里有的顺位男主依次选上，不够 5 人从名单上往下补，还不够就随机补齐。"
         "第二页（单人）：第 1 顺位 → 不在就免费刷新一次 → 第 2~5 顺位 → 都没有就随机。"
         "选了第 1 顺位后会出现第 2 顺位，已选过的男主不会再出现；选完第 4 顺位，剩下那位自动排第 5。")


def slot_override(k, man):
    return OD([
        (f'日程_人名_{k}', {'expected': OCR_ALIAS.get(man, man)}),
        (f'日程_选人_{k}', {'enabled': True}),
        (f'日程_一页_选_{k}_点', {'enabled': True}),
    ])


def option_name(k, chosen):
    return '日程第1顺位' if k == 1 else f'日程第{k}顺位（除{"、".join(chosen)}）'


def build():
    options = OD()

    def make(k, chosen):
        name = option_name(k, chosen)
        cases = [OD(name='不指定')]
        for man in MEN:
            if man in chosen:
                continue
            ov = slot_override(k, man)
            if k == 1:
                ov['日程_一页_顺位'] = {'enabled': True}
                ov['日程_二页_选人'] = {'enabled': True}
                ov['日程_二页_刷新'] = {'enabled': True}
            case = OD(name=man, pipeline_override=ov)
            rest = [m for m in MEN if m not in chosen and m != man]
            if k < 4:
                case['option'] = [make(k + 1, chosen + [man])]
            elif rest:  # 第 4 顺位选完，剩下的那位自动第 5
                ov.update(slot_override(5, rest[0]))
            cases.append(case)
        opt = OD(type='select', label=f'日程第{k}顺位', default_case='不指定')
        if k == 1:
            opt['description'] = DESC1
        opt['cases'] = cases
        options[name] = opt
        return name

    make(1, [])
    return options


def main():
    p = ROOT / 'assets/tasks/Schedule.json'
    data = json.loads(p.read_text(encoding='utf-8'), object_pairs_hook=OD)
    data['task'][0]['option'] = ['日程第1顺位']
    keep = OD((k, v) for k, v in data.get('option', {}).items() if not k.startswith('日程第'))
    keep.update(build())
    data['option'] = keep
    p.write_text(json.dumps(data, ensure_ascii=False, indent=4) + '\n', encoding='utf-8')
    c = ROOT / 'assets/tasks/Campus.json'
    campus = json.loads(c.read_text(encoding='utf-8'), object_pairs_hook=OD)
    opts = campus['task'][0]['option']
    first = next(i for i, o in enumerate(opts) if o.startswith('日程第'))
    opts[:] = [o for o in opts if not o.startswith('日程第')]
    opts.insert(first, '日程第1顺位')
    c.write_text(json.dumps(campus, ensure_ascii=False, indent=4) + '\n', encoding='utf-8')
    print('options:', len(data['option']))


if __name__ == '__main__':
    main()
