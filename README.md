# Hades 立绘构建、校验与安装恢复工具

Tools for building, validating, installing and restoring custom portraits in **Hades (the first game)** on macOS Steam.

本项目作用于《哈迪斯／Hades》一代的 macOS Steam 资源包，收录扎格列欧斯与宙斯两条静态立绘适配流程。用途是把自行准备的透明 PNG 适配到游戏原有 Sprite 画布，构建独立图集，再以哈希检查、暂存文件和恢复备份管理安装。它不改变移动、战斗逻辑。

**这是制作工具源码，不是可直接安装的美术 Mod。** 私人立绘、预览、生成提示词、原游戏资源包及原版备份均未公开。需要自行取得游戏、准备有权使用的图片，并从自己的游戏资源导出所需元数据。

## 收录范围

| 文件 | 用途 |
| --- | --- |
| `tools/build_zagreus.py` | 适配扎格列欧斯的十个目标条目；处理默认、BC3、720p 三套资源，保存原纹理、引用及非目标元数据 |
| `tools/verify_zagreus.py` | 对构建结果进行包回读、像素、Sprite 引用计数、原纹理及非目标元数据检查 |
| `tools/build_zeus.py` | 宙斯三个指定条目的透明图适配，处理预乘 Alpha、图集边缘留白并进行像素回读 |
| `packages/*/安装或恢复.py` | 对本地构建包执行 `check`、`install` 或 `restore`，保留原版 SHA、暂存与异常回滚 |

原项目还有其他角色及主菜单重影修复尝试。本仓库没有收录这些角色的私人素材，也不把所有历史方案包装成通用补丁。

## 环境与依赖

- Python 3.9 或更高版本。
- Pillow、numpy，以及兼容本脚本接口的 [quaerus/deppth](https://github.com/quaerus/deppth)。deppth 是第三方解析工具，不随仓库附带；需自行按上游许可取得。
- 自己安装的 macOS Steam 版 Hades。Windows 路径和包版本未在本次整理中验证。

可先使用独立 Python 环境安装公开依赖：

```sh
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install Pillow numpy
```

脚本会查找 `tools/deppth-master` 和 `tools/deps`，也可使用 Python 环境中已安装的对应模块。这些依赖目录已忽略，不要把下载的第三方整库或二进制混入自己的提交。

默认游戏包目录基于当前用户目录计算。安装位置不同时，显式设置：

```sh
export HADES_PACKAGES_DIR="/path/to/Hades/Game.macOS.app/Contents/Resources/Content/macOS/Packages"
```

## 自备输入与构建

先在独立工作副本中准备输入，不能指向唯一一份未备份的私人作品。游戏输入应是自己确认的干净原版；已安装旧替换时先用旧包恢复。若把已经修改的资源作为“原版”输入，新的恢复操作只能回到该输入状态。

- 扎格列欧斯：将对应透明 PNG 与 `原版相关静态资源.json` 元数据放到 `inputs/zagreus/`。JSON 沿用原适配流程的 `name`、`rect`、`topLeft`、`originalSize`、`scaleRatio` 字段；脚本预期 GUI 包九个目标、DeathArea 包一个目标，不是任意 PNG 的批量导入器。
- 宙斯：在 `inputs/zeus/` 自备 `Portraits_Zeus_01_透明.png`、`CodexPortrait_Zeus.png`、`Zeus_Hades_Handshake_02.png`。这些文件名对应游戏原有三个条目，不附图片内容。

```sh
python3 tools/build_zagreus.py
python3 tools/verify_zagreus.py
# 或单独构建宙斯流程
python3 tools/build_zeus.py
```

输出位于 `packages/zagreus/` 或 `packages/zeus/`，包括本机原版备份、安装资源、安装清单和检查报告。Zagreus 流程使用 `原版备份/`，Zeus 流程使用 `安装前备份/`。这些输出与私人输入已加入忽略规则。

缺少对应图片、元数据或包版本时，构建不会成为可用补丁；请先补齐自己的合法输入，不要从陌生第三方安装包复制未知清单。

## 安装、检查与恢复

先完全退出 Hades。下列命令以本机已经构建完成的宙斯包为例；替换为 `zagreus` 可操作另一条流程。

```sh
python3 packages/zeus/安装或恢复.py check
python3 packages/zeus/安装或恢复.py install
python3 packages/zeus/安装或恢复.py restore
```

`check` 读取游戏资源哈希并更新本机状态报告，不写游戏资源。安装或恢复前会确认游戏已退出，核对目标、原版和替换文件 SHA，再写同目录暂存文件并替换；异常时尝试回滚。清单中的绝对路径、上级路径及越出游戏目录的目标会被拒绝。

游戏更新、Steam 校验文件或其他 Mod 可能改变资源哈希。遇到版本不匹配时应重新从当前原版构建，不能删除检查或强行替换。恢复需要保留完整构建目录中的备份，不删除备份后再运行卸载。

## 本次验证与边界

本次只整理源码、改用当前用户默认路径和可配置游戏目录、分离私人输入，并对安装器的路径约束和安装/恢复流程做临时合成文件检查。没有读取、重建或安装任何真实游戏包，没有生成或公开私人图片。

历史项目曾做包回读、非目标数据保持、安装哈希等离线检查；它们不等于本次重新完成的游戏画面验证。所有角色、菜单效果以及 Windows 兼容性均未在本次实机复验。

```sh
python3 -m unittest discover -s tests -v
```

本仓库不附原游戏资源，也没有替第三方依赖或角色美术授予再分发许可。公开范围仅为这里列出的制作代码和说明。
