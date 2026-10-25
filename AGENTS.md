# MaaSH 开发守则

给参与开发的人和 AI 看。改动前先读完。

## 项目结构

```text
assets/interface.json        # GUI 定义：控制器、资源、导入哪些任务
assets/tasks/*.json          # 每个任务一个文件：任务名、入口节点、选项
assets/resource/pipeline/    # 流程节点（按功能分文件）
assets/resource/image/       # 模板图，按任务分子文件夹
assets/resource/model/ocr/   # OCR 模型（打包时从 MaaCommonAssets 复制）
assets/resource_bilibili/    # B服增量包，加载在共用资源后
tools/                       # 打包、校验脚本
```

## 硬性规则

1. **没有截图不写识别。** 每个识别节点都要有用户提供的 1280×720 原图、ROI 和界面跳转关系。还没截图的节点保持 `"enabled": false`，并在 `desc` 写明「待截图：xxx」。
2. **每个任务以 `Flag_` 节点收尾。** `Flag_` 节点必须识别到「已完成 / 已领取」的画面才算成功，不能只靠流程走完。外部验收器按日志里是否出现 `Flag_` 节点判断成功。
3. **超时和卡住统一落到 `公共_任务失败`。** 每个任务的等待节点都要写 `timeout` 和 `on_error: ["公共_任务失败"]`，记 Red 日志后跳过，不卡死整个流程。
4. **focus 日志颜色**：Limegreen=完成，Red=出错，Dimgray=信息，Orange=消极，Deepskyblue=积极。写法：`"[color:Limegreen]文字[/color]"`。
5. **不用硬延迟。** 优先 `pre_wait_freezes` / `post_wait_freezes` 或中间识别节点；`pre_delay` / `post_delay` 只在确实无法识别时使用，并在 `desc` 说明原因。
6. **盲点击必须加 `max_hit`。** 返回键、关公告、点空白这类会反复命中的节点同样要加。
7. **`next` 要覆盖所有可能出现的画面。** 弹窗用 `[JumpBack]` 挂在等待节点上，处理完回到原流程继续判断。新增通用弹窗时，同时加进 `启动_等待主界面`、`启动_主界面初判`、`公共_返回主界面` 的 `next`。
8. **坐标、ROI、模板图一律以 1280×720 为基准。** 游戏是横屏，模拟器可保持竖屏（游戏自己转屏）。
9. **不写死设备信息。** ADB 地址由用户在 GUI 里选择或填写；包名只写在 `StartApp` / `StopApp` 节点里。
10. **安全边界**：只截图 + 模拟点击。不注入、不读写内存、不改客户端文件、不走云端 API。不点任何付费或消耗钻石的确认按钮。唯一例外：「🛒月卡每周购买」（`weekly_shop.json`）按用户要求花 1200 钻石买「超值颜料礼盒」，默认不勾选，只在标题和价签都核对通过时才点；新增任何花钻石的功能都必须先得到用户明确同意、默认关闭、并核对商品名和价格。

## 命名

- 节点名用中文，前缀表示归属：`启动_`、`公共_`、`签到_`……；完成确认统一用 `Flag_`。
- 模板图放在 `image/<任务名>/`，文件名和节点名对应。
- 资源路径一律用正斜杠。

## 提交前

```bash
python tools/validate_schema.py --schema-dir deps/tools --resource-dirs assets/resource assets/resource_bilibili --exclude-dirs assets/resource/announcement --interface-files assets/interface.json --task-dirs assets/tasks
python tools/lint_pipeline.py   # And/Or 包装、节点引用、模板图
```

提交信息遵循 [Conventional Commits](https://www.conventionalcommits.org/)：`feat` / `fix` / `docs` / `ci` / `chore` 等。

## 参考项目

- [MaaPracticeBoilerplate](https://github.com/MaaXYZ/MaaPracticeBoilerplate)（MIT）：项目骨架、打包流程。
- [MaaLYSK](https://github.com/Witty36/MaaLYSK)（MIT）：任务拆分、启动循环、弹窗兜底的写法。
- [M9A](https://github.com/MaaXYZ/M9A)、[明日方舟 MAA](https://github.com/MaaAssistantArknights/MaaAssistantArknights)（AGPL）：只参考思路，不复制代码。
