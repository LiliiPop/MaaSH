"""速写：按 tools/sketch/icons.json 生成灵感图标模板。

  src=game：tools/sketch_src/game/<file>.png 是实机截的单个图标（100%，背景已涂成纯绿 0,255,0 供 green_mask），
            缩放成 60%~160% 共 12 张 → assets/resource/image/sketch/灵感/<file>_<比例>.png
  src=wiki：tools/sketch_src/wiki/levels.npy（灰机 wiki 图标，56×56、16 级灰度）+ names.json，
            裁到图标外框、按宽 28~80（每 2px）缩放、灰度映射到实机气泡的金色（深 BGR 60,105,150 → 浅 125,195,240），
            背景涂纯绿 → assets/resource/image/sketch/wiki/<题材>_<宽>.png

默认只补缺的文件（已有的不动，11-13 生成的那批保持原样）；加 --force 全部重新生成。
新截到实机图标：抠好放进 sketch_src/game/，icons.json 里把该题材改成 {"src": "game", "file": "<文件名>"}，再跑本脚本和 gen_sketch.py。
"""
import json
import os
import sys

import cv2
import numpy as np

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
SRC = os.path.join(ROOT, 'tools/sketch_src')
OUT = os.path.join(ROOT, 'assets/resource/image/sketch')
GAME_SCALES = [60, 67, 75, 85, 92, 100, 108, 115, 125, 140, 150, 160]
WIKI_WIDTHS = list(range(28, 81, 2))
DARK = np.array([60, 105, 150], np.float32)
LIGHT = np.array([125, 195, 240], np.float32)
GREEN = (0, 255, 0)
force = '--force' in sys.argv


def write(path, img):
    if force or not os.path.exists(path):
        cv2.imencode('.png', img)[1].tofile(path)
        return 1
    return 0


icons = json.load(open(os.path.join(ROOT, 'tools/sketch/icons.json'), encoding='utf-8'))
levels = np.load(os.path.join(SRC, 'wiki/levels.npy'))
wiki_names = json.load(open(os.path.join(SRC, 'wiki/names.json'), encoding='utf-8'))
os.makedirs(f'{OUT}/灵感', exist_ok=True)
os.makedirs(f'{OUT}/wiki', exist_ok=True)
made = 0
for theme, ic in icons.items():
    if ic['src'] == 'game':
        for f in [ic["file"]] + ic.get("extra", []):  # extra：同一题材在不同气泡里画法略有差别时，多截几张（11-23 运动）
            src = cv2.imdecode(np.fromfile(f'{SRC}/game/{f}.png', np.uint8), cv2.IMREAD_COLOR)
            h, w = src.shape[:2]
            for s in GAME_SCALES:
                size = (max(1, round(w * s / 100)), max(1, round(h * s / 100)))
                img = cv2.resize(src, size, interpolation=cv2.INTER_AREA if s < 100 else cv2.INTER_LINEAR)
                made += write(f'{OUT}/灵感/{f}_{s}.png', img)
    else:
        lv = levels[wiki_names.index(ic['file'])]
        ys, xs = np.nonzero(lv)
        a = lv[ys.min():ys.max() + 1, xs.min():xs.max() + 1].astype(np.float32) / 15
        h, w = a.shape
        for W in WIKI_WIDTHS:
            r = cv2.resize(a, (W, round(W * h / w)), interpolation=cv2.INTER_AREA)
            img = np.clip(np.round(DARK + r[..., None] * (LIGHT - DARK)), 0, 255).astype(np.uint8)
            img[r < 0.5 / 15] = GREEN
            made += write(f'{OUT}/wiki/{ic["file"]}_{W}.png', img)
print(f'生成 {made} 张模板（{"全部重做" if force else "只补缺的"}）')
