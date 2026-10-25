"""Update saved local task lists without resetting devices or existing selections.

Close the client first. Usage: python tools/sync_local_tasks.py --client-dir install
"""
import argparse
import copy
from datetime import datetime
import json
from pathlib import Path
import shutil


def migrate_instance(data, sketch, resource='B服'):
    data = copy.deepcopy(data)

    def rename(value):
        if isinstance(value, dict):
            return {k: rename(v) for k, v in value.items()}
        if isinstance(value, list):
            return [rename(v) for v in value]
        if isinstance(value, str):
            if value == '✈️启动绘旅人':
                return '✈️启动游戏'
            return value.replace('✈️启动绘旅人<|||>', '✈️启动游戏<|||>')
        return value

    data = rename(data)
    items = data.setdefault('TaskItems', [])
    existing = next((t for t in items if t.get('entry') == '速写'), None)
    if existing is None:
        item = copy.deepcopy(sketch)
        item['option'] = [{'name': name, 'index': 0} for name in item.get('option', [])]
        position = next((i + 1 for i, t in enumerate(items) if t.get('entry') == '校园合一'), len(items))
        items.insert(position, item)
    else:
        existing['group'] = ['daily']
    current = data.setdefault('CurrentTasks', [])
    if not any(name.endswith('<|||>速写') for name in current):
        position = next((i + 1 for i, name in enumerate(current)
                         if name.endswith('<|||>校园合一')), len(current))
        current.insert(position, '✏️速写<|||>速写')
    previous_resource = data.get('Resource')
    options = data.setdefault('ResourceOptionItems', {})
    if resource not in options and previous_resource in options:
        options[resource] = copy.deepcopy(options[previous_resource])
    data['Resource'] = resource
    return data


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--client-dir', type=Path, default=Path('install'))
    args = parser.parse_args()
    client = args.client_dir.resolve()
    sketch = json.loads((client / 'tasks/Sketch.json').read_text(encoding='utf-8'))['task'][0]
    paths = sorted((client / 'config/instances').glob('*.json'))
    backup = client.parent / 'debug/config-backups' / datetime.now().strftime('%Y%m%d-%H%M%S')
    for path in paths:
        data = json.loads(path.read_text(encoding='utf-8-sig'))
        updated = migrate_instance(data, sketch)
        if updated != data:
            backup.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, backup / path.name)
            path.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Synchronized {len(paths)} configurations; previous versions backed up under debug/config-backups')
