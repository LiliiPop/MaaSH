"""Verify the four requested integrations without input to the game."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8'))


class FeatureIntegrationTests(unittest.TestCase):
    def test_startup_keeps_name_and_sketch_not_shipped(self):
        interface = load('assets/interface.json')
        startup_task = load('assets/tasks/StartUp.json')['task'][0]
        self.assertEqual(startup_task['name'], '✈️启动绘旅人')  # 任务名不变，已存配置和管家预设按名字对应
        self.assertEqual(startup_task['label'], '✈️启动游戏')
        self.assertNotIn('tasks/Sketch.json', interface['import'])  # 速写待贡献者完善退出机制后再提交
        for preset in interface['preset']:
            names = [t['name'] for t in preset['task']]
            self.assertIn('✈️启动绘旅人', names)
            self.assertNotIn('✏️速写', names)
        tasks = [task for path in interface['import'] for task in load('assets/' + path).get('task', [])]
        self.assertFalse(any(task['name'].startswith('HLR_') for task in tasks))

    def test_schedule_priority_only_changes_second_page(self):
        task = load('assets/tasks/Schedule.json')
        self.assertEqual(task['task'][0]['option'], [f'日程第{i}顺位' for i in range(1, 6)])
        original = load('assets/resource/pipeline/schedule.json')
        imported = load('assets/resource/pipeline/schedule_selected.json')
        self.assertNotIn('日程_指定_翻页', imported)
        self.assertEqual(imported['日程_二页_选人']['next'][0], '日程_选人_1')
        self.assertEqual(imported['日程_二页_选人']['next'][-1], '日程_二页_随机')
        for i in range(1, 6):
            option = task['option'][f'日程第{i}顺位']
            self.assertEqual(option['default_case'], '不指定')
            self.assertNotIn('pipeline_override', option['cases'][0])
            self.assertEqual([c['name'] for c in option['cases'][1:]], ['艾因', '路辰', '罗夏', '司岚', '叶瑄'])
            for case in option['cases'][1:]:
                override = case['pipeline_override']
                self.assertTrue(override[f'日程_选人_{i}']['enabled'])
                self.assertIn(case['name'], json.dumps(override, ensure_ascii=False))
                self.assertTrue(override['日程_二页_选人']['enabled'])
                self.assertTrue(override['日程_一页_随机']['enabled'])
                self.assertNotIn('日程_流程', override)
                self.assertNotIn('日程_随机选择', override)
            self.assertFalse(imported[f'日程_选人_{i}']['enabled'])
            self.assertEqual(imported[f'日程_选人_{i}']['next'], ['日程_指定_日程确定2'])
        self.assertIn('[JumpBack]日程_翻页', original['日程_流程']['next'])
        self.assertIn('Flag_日程完成', imported['日程_指定_寻找信封']['next'])
        campus = load('assets/tasks/Campus.json')['task'][0]
        for i in range(1, 6):
            self.assertIn(f'日程第{i}顺位', campus['option'])
        self.assertEqual(campus['pipeline_override']['Flag_日程完成']['next'], ['校园_日程做完'])

    def test_theater_has_three_switches(self):
        definition = load('assets/tasks/Theater.json')
        task = definition['task'][0]
        self.assertEqual(task['name'], '🎭手偶剧场三合一')  # 内部名不变（已存配置、管家按名字对应）
        self.assertEqual(task['entry'], '剧场三合一')
        self.assertEqual(task['option'], ['剧场点赞', '剧场评论', '领取观影券进度奖励'])
        self.assertNotIn('pipeline_override', task)
        like = {c['name']: c for c in definition['option']['剧场点赞']['cases']}
        self.assertEqual(like['No']['pipeline_override']['剧场_等播放']['next'], ['剧场_不点赞_返回'])
        comment = {c['name']: c for c in definition['option']['剧场评论']['cases']}
        self.assertEqual(comment['Yes']['pipeline_override']['剧场_点第一部']['next'], ['剧场_评论_唤出'])
        self.assertEqual(comment['Yes']['option'], ['评论内容'])
        option = definition['option']['领取观影券进度奖励']
        self.assertEqual(option['cases'][0]['pipeline_override']['剧场_完成']['next'], ['剧场_领券_完成'])
        self.assertEqual(option['cases'][1]['pipeline_override']['剧场_完成']['next'], [])
        interface = load('assets/interface.json')
        self.assertNotIn('tasks/TheaterLike.json', interface['import'])
        tickets = load('assets/resource/pipeline/theater_tickets.json')
        self.assertFalse(any(n.get('action') == 'InputText' for n in tickets.values()))

    def test_bilibili_covers_every_lifecycle_node_and_gates_account_matching(self):
        overlay = load('assets/resource_bilibili/pipeline/server.json')
        for path in (ROOT / 'assets/resource/pipeline').glob('*.json'):
            for name, node in json.loads(path.read_text(encoding='utf-8')).items():
                action = node.get('action')
                kind = action.get('type') if isinstance(action, dict) else action
                if kind in ('StartApp', 'StopApp'):
                    self.assertEqual(overlay[name]['action']['param']['package'], 'com.netease.skzdhlr.bilibili')
        startup = load('assets/tasks/StartUp.json')['option']
        self.assertEqual(startup['使用指定账号登录']['resource'], ['官服'])
        self.assertEqual(startup['B服登录记录核对']['resource'], ['B服'])
        self.assertEqual(startup['B服登录记录核对']['default_case'], '关闭')
        handlers = load('assets/resource/pipeline/bilibili.json')
        self.assertFalse(handlers['B服_账号选择等待登录记录']['enabled'])
        self.assertEqual(handlers['B服_sub_登录账号']['all_of'][0], 'B服_登录记录标识')
        enabled = startup['B服登录记录核对']['cases'][1]['pipeline_override']
        self.assertFalse(enabled['B服_sub_登录账号']['enabled'])
        self.assertTrue(enabled['B服_账号选择等待登录记录']['enabled'])


if __name__ == '__main__':
    unittest.main()
