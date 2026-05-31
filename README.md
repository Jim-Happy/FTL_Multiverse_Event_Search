# FTLSearch

FTLSearch 是一个面向《FTL: Faster Than Light》及其 Multiverse 模组的事件查询工具。项目通过 SQLite 数据库读取已经解析好的事件数据，并提供中文界面的搜索、交互式浏览和事件树追踪，方便快速定位事件分支、查看文本内容和奖励效果。

## 功能

- 支持按事件名称、关键字或 ID 搜索节点。
- 交互模式下可直接点击事件选项、随机分支和战斗分支继续浏览。
- 事件树模式支持按需展开节点，适合查看复杂的网状剧情结构。
- 内置循环检测，避免在有回环的事件链中无限展开。
- 可展示并格式化部分奖励与效果信息，配合本地翻译字典提升可读性。
- 支持在桌面程序和 PyInstaller 打包后的独立程序中使用。

## 运行环境

- Python 3.12 或更高版本
- `uv`
- PyQt6

## 安装与运行

1. 克隆仓库后进入项目目录。
2. 安装依赖：

```bash
uv sync
```

3. 启动程序：

```bash
uv run main.py
```

## 数据库准备

程序启动时会优先查找以下数据库文件：

- 当前工作目录下的 `ftl_output.sqlite`
- 当前工作目录下的 `ftl_output.db`
- 打包后可执行文件同目录下的同名数据库
- 打包资源目录中的同名数据库

如果你已经有解析好的 SQLite 数据库，只要把它命名为 `ftl_output.sqlite` 或 `ftl_output.db` 并放到程序可访问的位置即可直接运行。

仓库中提供了 SQLite 预处理脚本，可将 FTL 的 XML 数据转换为数据库：

```bash
uv run python gameDataAnalyzer/sqlCreate/ftl_sqlite_preprocessor.py gameDataAnalyzer/sqlCreate/gamedata --db ftl_output.sqlite
```

如果你不想改输出名，也可以先生成默认数据库，再将结果复制或重命名为 `ftl_output.sqlite`，这样主程序可以自动识别。

## 打包

项目已提供 PyInstaller 配置文件 [FTLSearch.spec](FTLSearch.spec)。在确认 `ftl_output.sqlite` 与图标文件存在后，可以使用 PyInstaller 生成独立程序。

## 目录说明

- [main.py](main.py) : 程序入口，启动 GUI。
- [ftl_gui/](ftl_gui) : 图形界面与交互逻辑。
- [ftl_dao.py](ftl_dao.py) : SQLite 数据访问层。
- [gameDataAnalyzer/](gameDataAnalyzer) : XML 解析、数据预处理与翻译相关脚本。
- [icon/](icon) : 程序图标资源。

## 说明

- 本项目当前界面语言为中文。
- 若数据库为空，界面会显示示例内容，但完整功能需要加载真实的事件数据库。
- `translation_dict.py` 和相关翻译文件用于将部分效果、种族、武器和资源名转换为中文。

## 致谢

感谢 FTL 汉化组、Slipstream Mod Manager 开发者以及各位 FTL Mod 作者提供的资料与启发。
