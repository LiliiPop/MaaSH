"""Migrate only Sketch, selected schedule character, theater tickets and Bilibili.

Run with --source <MaaHLR checkout>. Reads the existing HLR pipeline and templates;
does not import other HLR tasks or run the game.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=4) + '\n', encoding='utf-8')


def migrate(source):
    assets = ROOT / 'assets'
    original = source / 'assets'
    source_interface = load(original / 'interface.json')
    used_files = {original / 'interface.json', source / 'LICENSE'}
    templates = set()

    def read_source(stem):
        path = original / 'resource/pipeline' / (stem + '.json')
        used_files.add(path)
        return load(path)

    def converter(mapping, expand_campus=False):
        def ref(value):
            flags, name = re.fullmatch(r'((?:\[[^]]+\])*)(.*)', value).groups()
            if name not in mapping:
                raise ValueError(f'Unmapped source reference: {name}')
            return flags + mapping[name]

        def convert(value, key=''):
            if isinstance(value, list):
                result = []
                for item in value:
                    converted = convert(item, key)
                    if key not in ('next', 'on_error') or converted not in result:
                        result.append(converted)
                    if expand_campus and key in ('next', 'on_error') and isinstance(item, str):
                        if item == '[JumpBack]进入校园':
                            result.append('[JumpBack]日程_指定_进入校园_默认')
                return result
            if isinstance(value, dict):
                if key == 'pipeline_override':
                    return {ref(k): convert(v) for k, v in value.items()}
                return {k: convert(v, k) for k, v in value.items()}
            if isinstance(value, str):
                if key == 'template':
                    templates.add(value)
                    return 'hlr/' + value
                if key in ('next', 'on_error', 'all_of', 'any_of', 'roi', 'target', 'begin', 'end'):
                    return ref(value)
            return value
        return convert

    def prepare(node, description):
        node.setdefault('desc', description + '；沿用 HLR 已有截图、识别与动作。原延迟用于点击后画面过渡，待实测后再改为识别等待。')
        if node.get('next'):
            node.setdefault('timeout', 15000)
            node.setdefault('on_error', ['公共_任务失败'])
        if node.get('action') in ('Click', 'Swipe', 'MultiSwipe'):
            node.setdefault('max_hit', 10)
        return node

    common = load(assets / 'resource/pipeline/common.json')
    campus = load(assets / 'resource/pipeline/campus.json')

    # 1. One new opt-in Sketch task. Reuse SH home/campus routing, not HLR preflight.
    sketch_source = read_source('sketch')
    sketch_map = {k: '速写_' + k.removeprefix('速写').removeprefix('_') for k in sketch_source}
    sketch_map['完成启动_确认'] = 'Flag_速写已返回主页'
    sketch_convert = converter(sketch_map)
    sketch = {sketch_map[k]: prepare(sketch_convert(v), '速写移植')
              for k, v in sketch_source.items() if k not in ('速写', '速写进入校园')}
    sketch['速写'] = {'desc': '速写任务入口，先归位；仅支持已接入的四种题型。',
                     'timeout': 30000,
                     'next': ['速写_进入校园', '速写_进入校园_默认', '[JumpBack]公共_返回主界面'],
                     'on_error': ['公共_任务失败']}
    for suffix in ('', '_默认'):
        node = copy.deepcopy(campus['校园_主界面进校园' + suffix])
        node.update(next=['速写_点击入口'], max_hit=3, timeout=20000,
                    on_error=['公共_任务失败'], desc='速写复用 SH 的校园入口，区分主页主题。')
        sketch['速写_进入校园' + suffix] = node
    sketch['Flag_速写已返回主页'] = {
        'desc': '结束时识别主界面；是否实际赠送以速写结算画面和运行日志为准。',
        'recognition': copy.deepcopy(common['Flag_在主界面']['recognition']),
        'focus': {'Node.Action.Succeeded': '[color:Limegreen]速写流程结束，已返回主页[/color]'}}
    sketch_option = sketch_convert(source_interface['option']['速写男主'])
    write(assets / 'resource/pipeline/sketch.json', sketch)
    write(assets / 'tasks/Sketch.json', {
        'task': [{'name': '✏️速写', 'entry': '速写', 'group': ['daily'],
                  'default_check': False, 'option': ['速写男主'],
                  'description': 'tasks/doc/Sketch.md'}],
        'option': {'速写男主': sketch_option}})

    # 2. Enhance the existing schedule task; no parallel HLR schedule task.
    schedule_source = read_source('itinerary')
    schedule_map = {k: '日程_指定_' + k for k in schedule_source}
    schedule_map.update({'完成启动_确认': 'Flag_日程指定男主已返回主页',
                         '日程返回主页确认': 'Flag_日程指定男主已返回主页',
                         '完成日程': 'Flag_日程完成',
                         '日程今日已完成': 'Flag_日程今日已完成',
                         '进入校园': '日程_指定_进入校园',
                         '返回主界面1': '公共_返回主界面',
                         '返回主界面3': '公共_返回主界面'})
    convert_schedule = converter(schedule_map, expand_campus=True)
    excluded = {'日程', '进入日程', '日程确定1', '下一项日程', '日程_执行流程',
                '完成日程', '日程今日已完成', '日程关闭页面', '日程返回校园', '日程返回主页确认',
                *(f'点击角色{i}' for i in range(1, 6))}
    schedule_nodes = {schedule_map[k]: prepare(convert_schedule(v), '指定男主日程移植')
                      for k, v in schedule_source.items() if k not in excluded}
    sh_schedule = load(assets / 'resource/pipeline/schedule.json')
    # Preserve SH's first-page random selection. Only its page-turn transitions
    # into HLR's second-page character selector and subsequent map/dialogue flow.
    page_turn = copy.deepcopy(sh_schedule['日程_翻页'])
    page_turn.update(next=[schedule_map['点击角色6']], on_error=['公共_任务失败'])
    schedule_nodes['日程_指定_翻页'] = page_turn
    write(assets / 'resource/pipeline/schedule_selected.json', schedule_nodes)
    schedule_option = convert_schedule(source_interface['option']['日程第二项男主'])
    schedule_option['default_case'] = '沿用随机'
    schedule_option['cases'].insert(0, {'name': '沿用随机'})
    for case in schedule_option['cases'][1:]:
        case['pipeline_override']['日程_流程'] = {
            'next': ['日程_指定_翻页' if ref == '[JumpBack]日程_翻页' else ref
                     for ref in sh_schedule['日程_流程']['next']]}
        case['pipeline_override']['日程_随机选择'] = {
            'recognition': {'type': 'And', 'param': {'all_of': [
                {'recognition': copy.deepcopy(sh_schedule['日程_随机选择']['recognition'])},
                {'recognition': copy.deepcopy(sh_schedule['日程_翻页']['recognition'])}
            ]}}}
    schedule_task = load(assets / 'tasks/Schedule.json')
    schedule_task['task'][0]['option'] = ['日程第二项男主']
    schedule_task.setdefault('option', {})['日程第二项男主'] = schedule_option
    write(assets / 'tasks/Schedule.json', schedule_task)
    campus_task = load(assets / 'tasks/Campus.json')
    if '日程第二项男主' not in campus_task['task'][0].setdefault('option', []):
        campus_task['task'][0]['option'].append('日程第二项男主')
    write(assets / 'tasks/Campus.json', campus_task)

    # 3. Add only the ticket reward tail; SH watch/like/comment stays intact.
    theater_source = read_source('puppet')
    ticket_keys = ['手偶剧场完成', '手偶剧场观影券奖励确认',
                   '手偶剧场观影券奖励关闭', '手偶剧场退出社交']
    ticket_map = {k: '剧场_领券_' + k.removeprefix('手偶剧场') for k in ticket_keys}
    ticket_map.update({'完成启动_确认': 'Flag_剧场领券后已返回主页'})
    convert_ticket = converter(ticket_map)
    tickets = {ticket_map[k]: prepare(convert_ticket(theater_source[k]), '观影券领取移植')
               for k in ticket_keys}
    for key in ('手偶剧场观影券奖励确认', '手偶剧场观影券奖励关闭'):
        name = ticket_map[key]
        tickets[name]['focus'] = {'Node.Action.Succeeded': '[color:Limegreen]已处理观影券奖励弹窗[/color]'}
    tickets['Flag_剧场领券后已返回主页'] = {
        'recognition': copy.deepcopy(common['Flag_在主界面']['recognition']),
        'desc': '剧场领取流程返回主页；无奖励弹窗时不声称领到新观影券。'}
    write(assets / 'resource/pipeline/theater_tickets.json', tickets)
    theater_task = load(assets / 'tasks/Theater.json')
    if '领取观影券进度奖励' not in theater_task['task'][0]['option']:
        theater_task['task'][0]['option'].append('领取观影券进度奖励')
    theater_task['option']['领取观影券进度奖励'] = {
        'type': 'select', 'default_case': '开启',
        'description': '三合一完成后尝试领取社交页观影券进度奖励；已领过或没有奖励弹窗时正常返回。',
        'cases': [{'name': '开启', 'pipeline_override': {'剧场_完成': {'next': [ticket_map['手偶剧场完成']]}}},
                  {'name': '关闭', 'pipeline_override': {'剧场_完成': {'next': []}}}]}
    write(assets / 'tasks/Theater.json', theater_task)

    # 4. Channel lifecycle override + Bilibili login record/popup handling.
    account_source = read_source('account')
    start_source = read_source('start')
    bmap = {k: 'B服_' + k for k in account_source}
    bmap['B服登录记录标识'] = 'B服_登录记录标识'
    bmap.update({k: 'B服_' + k for k in ('sub_登录账号', 'sub_隐私政策关闭', 'sub_网易协议关闭')})
    bmap.update({'启动游戏': 'B服_继续启动', '启动界面检查': 'B服_继续启动'})
    convert_b = converter(bmap)
    bnodes = {bmap[k]: prepare(convert_b(v), 'B服登录记录移植') for k, v in account_source.items()}
    bnodes[bmap['账号选择等待登录记录']]['enabled'] = False
    # A JumpBack login handler returns to SH's existing startup wait, never restarts the app.
    bnodes['B服_继续启动'] = {'desc': '结束 B服弹窗子流程，回到 SH 启动等待。'}
    for key in ('sub_登录账号', 'sub_隐私政策关闭', 'sub_网易协议关闭'):
        bnodes[bmap[key]] = prepare(convert_b(start_source[key]), 'B服启动弹窗移植')
    # Require the known login-record panel before the default login click.
    default_login = bnodes[bmap['sub_登录账号']]
    login_reco = {k: copy.deepcopy(v) for k, v in default_login.items()
                  if k in ('recognition', 'expected', 'roi')}
    for key in ('recognition', 'expected', 'roi'):
        default_login.pop(key, None)
    default_login.update(recognition='And', all_of=[bmap['B服登录记录标识'], login_reco], box_index=1)
    write(assets / 'resource/pipeline/bilibili.json', bnodes)
    overlay = {}
    for path in (assets / 'resource/pipeline').glob('*.json'):
        for name, node in load(path).items():
            action = node.get('action')
            kind = action.get('type') if isinstance(action, dict) else action
            if kind in ('StartApp', 'StopApp'):
                overlay[name] = {'action': {'type': kind, 'param': {'package': 'com.netease.skzdhlr.bilibili'}}}
    startup = load(assets / 'resource/pipeline/startup.json')
    handlers = ['[JumpBack]' + bmap[k] for k in ('账号选择等待登录记录', 'sub_登录账号',
                                                'sub_隐私政策关闭', 'sub_网易协议关闭')]
    for name in ('启动_等待主界面', '启动_主界面初判'):
        overlay[name] = {'next': handlers + startup[name]['next']}
    write(assets / 'resource_bilibili/pipeline/server.json', overlay)
    startup_task = load(assets / 'tasks/StartUp.json')
    startup_task['task'][0]['name'] = '✈️启动游戏'
    startup_task['option']['使用指定账号登录']['resource'] = ['官服']
    if 'B服登录记录核对' not in startup_task['task'][0]['option']:
        startup_task['task'][0]['option'].append('B服登录记录核对')
    startup_task['option']['B服登录记录核对'] = {
        'type': 'select', 'resource': ['B服'], 'default_case': '关闭',
        'description': '只核对已保存的 B服登录记录，不主动注销当前账号；找不到指定昵称时停止。',
        'cases': [{'name': '关闭'}, {'name': '开启', 'option': ['B服登录账号昵称'],
                  'pipeline_override': {bmap['账号选择等待登录记录']: {'enabled': True},
                                        bmap['sub_登录账号']: {'enabled': False}}}]}
    startup_task['option']['B服登录账号昵称'] = convert_b(source_interface['option']['B服登录账号昵称'])
    startup_task['option']['B服登录账号昵称']['resource'] = ['B服']
    write(assets / 'tasks/StartUp.json', startup_task)
    interface = load(assets / 'interface.json')
    interface['resource'][0]['label'] = '官服'
    for preset in interface['preset']:
        for task in preset['task']:
            if task['name'] == '✈️启动绘旅人':
                task['name'] = '✈️启动游戏'
        if not any(t['name'] == '✏️速写' for t in preset['task']):
            position = next((i + 1 for i, t in enumerate(preset['task'])
                             if t['name'] == '🏫校园合一'), len(preset['task']))
            preset['task'].insert(position, {'name': '✏️速写', 'enabled': False})
    if not any(r['name'] == 'B服' for r in interface['resource']):
        resource = copy.deepcopy(interface['resource'][0])
        resource.update(name='B服', label='B服', path=['./resource', './resource_bilibili'])
        interface['resource'].append(resource)
    if 'tasks/Sketch.json' not in interface['import']:
        interface['import'].append('tasks/Sketch.json')
    write(assets / 'interface.json', interface)

    for template in sorted(templates):
        path = original / 'resource/image' / template
        used_files.add(path)
        target = assets / 'resource/image/hlr' / template
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
    manifest = {'repository': 'https://github.com/MelinaQ/MaaHLR', 'license': 'MIT',
                'scope': ['速写', '日程第二项男主', '剧场观影券进度奖励', 'B服启动与登录记录'],
                'source': 'local working tree, including uncommitted changes',
                'sha256': {str(p.relative_to(source)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in sorted(used_files)}}
    write(ROOT / 'third_party/MaaHLR/source.json', manifest)
    shutil.copy2(source / 'LICENSE', ROOT / 'third_party/MaaHLR/LICENSE')
    print(f'Migrated four features; {len(templates)} referenced templates, one new task')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    migrate(parser.parse_args().source.resolve())
