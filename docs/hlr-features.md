# HLR 四项功能并入 SH

本分支只迁入以下四项，不复制 HLR 的整套任务列表，也不改动旁边的 MaaHLR 工作区。

| 功能 | 接入位置 | 默认行为 |
| --- | --- | --- |
| 速写完整流程 | 新增 `✏️速写`；选男主、收集、四类连线、赠送、返回主页 | 不勾选 |
| 日程第二项指定男主 | 原 `🗓️安排日程` 与 `🏫校园打包` 增加五位男主选项 | 沿用 SH 随机 |
| 观影券进度奖励 | 原 `🎭手偶剧场三合一` 增加领券收尾选项 | 开启，可关闭 |
| B服 | 新增 B服资源；原启动任务中增加登录记录核对选项 | 不核对指定账号 |

## 连接方式

- 速写复用 SH 的默认 / 全景 / 出行主题校园入口，进入后使用 HLR 的速写流程，不引入 HLR 的其他日常或主页归位流程。
- 指定日程保持 SH 第一页随机选择与翻页动作；第二页转入 HLR 的选人和场景处理。完成后回到 SH 原完成标记，因此校园打包可以继续画展。中途已经停在第二页的恢复状态仍待验证，不让 SH 随机选择覆盖指定角色。
- 剧场的观看、点赞和评论节点保持不变，只由现有任务的选项给 `剧场_完成` 追加领券收尾。无奖励弹窗时不宣称领到新奖励。
- B服先加载共用资源，再加载 `resource_bilibili`，覆盖所有启动 / 关闭节点和启动弹窗路由。官服历史账号切换只对官服显示，B服昵称核对默认关闭。验证码和首次账号登录仍需人工完成。

## 来源和验证

来源为 [MelinaQ/MaaHLR](https://github.com/MelinaQ/MaaHLR) 本地开发工作区（包含未提交改动），引用的源文件与模板 SHA-256 记录在 `third_party/MaaHLR/source.json`。MIT 许可证随源码和打包结果保留。

```powershell
python tools/migrate_hlr_features.py --source C:\path\to\MaaHLR
python -m unittest discover -s tests -v
python tools/lint_pipeline.py
python tools/validate_schema.py --schema-dir deps/tools --resource-dirs assets/resource assets/resource_bilibili --exclude-dirs assets/resource/announcement --interface-files assets/interface.json --task-dirs assets/tasks
```

迁移保留 HLR 已有识别、模板与连线路径，不臆造新题目或新坐标。新任务说明只注明现有能力；游戏内结果需在 SH 内逐项验证。

已通过配置 Schema、引用与模板检查、四项回归检查，以及 MaaFramework v5.14.3 的实际资源加载和五位男主、B服选项覆盖检查。没有自动运行游戏任务，也没有推送或发布安装包。原 SH 启动重开流程存在的两条嵌套路径本次保持不变。
