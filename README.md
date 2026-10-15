# MaaSH

「时空中的绘旅人」日常小助手，基于 [MaaFramework](https://github.com/MaaXYZ/MaaFramework)，图形界面使用 [MFAAvalonia](https://github.com/SweetSmellFox/MFAAvalonia)。

> 开发中，目前只有项目骨架，日常任务还不能使用。

只截图 + 模拟点击，不修改游戏、不读写内存。

## 支持情况

| 项目 | 状态 |
| --- | --- |
| 服务器 | 官服（包名 `com.netease.skzdhlr`） |
| 模拟器 | MuMu 模拟器 12（其他模拟器理论可用，未测试） |
| 分辨率 | 16:9，推荐 1280×720；游戏横屏，模拟器横竖屏均可 |

## 连接模拟器

MaaSH 打开后会自动查找正在运行的模拟器，在「连接」里选择你的模拟器即可。

如果没有自动找到，或者你开了多个模拟器，需要手动填写 ADB 地址：

1. 打开桌面上的「MuMu 多开器 12」。
2. 找到右上角或设置里的「ADB 端口」，展开后能看到每个模拟器一行，例如：

   ```text
   #0   上班模拟器   5555,16385
   ```

3. 取你运行游戏的那一行最后的数字（上例是 `16385`），在 MaaSH 的连接设置里填写 `127.0.0.1:16385`。

不同电脑、不同多开实例的端口可能不一样，请以你自己多开器里显示的为准。

## 任务列表

| 任务 | 说明 | 状态 |
| --- | --- | --- |
| ✈️启动绘旅人 | 启动游戏、点击登录、关闭公告，停在主界面 | 可用 |
| 🏁结束后操作 | 可选：关闭游戏 / 返回主界面 / 不动 | 可用 |
| 💤关闭绘旅人 | 关闭游戏 | 可用 |
| 🧪冒烟测试 | 开发用：确认能连上模拟器、能启动游戏 | 可用 |

## 日志

- `debug/maafw.log`：框架日志
- `logs/log-日期.log`：运行日志
- `debug/on_error/`：出错时的截图

## 开发

见 [AGENTS.md](./AGENTS.md)。

## 致谢

项目结构参考了 [MaaPracticeBoilerplate](https://github.com/MaaXYZ/MaaPracticeBoilerplate) 和 [MaaLYSK](https://github.com/Witty36/MaaLYSK)。
