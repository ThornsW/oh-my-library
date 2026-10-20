# Memo

Memo 是一个本地桌面待办和 Markdown 笔记应用。它使用 PySide6 构建界面,SQLite 保存数据,常驻系统托盘,当前主要维护 Linux 和 Windows。

## 功能

- 三栏工作区:标签栏、待办列表、详情编辑器
- 待办字段:标题、笔记、截止日期、优先级、标签、子任务
- 标签右键菜单:在该标签下直接新建待办、重命名标签、删除标签
- 列表筛选:未完成、全部、已完成;支持标签过滤和标题/笔记搜索
- Markdown 笔记编辑与预览
- 系统托盘常驻;关闭主窗口只隐藏到托盘
- 窗口置顶、开机自启、全局快捷键切换显示/隐藏
- 本地 SQLite 数据库,无网络依赖

### 在标签下新建待办

在左侧标签栏右键点击一个标签,选择「在此标签下新建待办…」,新建对话框会自动勾选该标签。创建完成后,列表会停留在这个标签上,方便直接确认新条目;如果在对话框里取消勾选了该标签,则回到「全部待办」。

## 环境要求

- Miniforge 或 Mambaforge
- Python 3.11 或更高
- PySide6 6.4 或更高
- Linux 中文输入:运行的桌面上有 fcitx5(默认启用 ibusfrontend)或 ibus
- Windows 全局快捷键:依赖 `pynput`

构建机的 Qt 版本不需要和用户桌面的 Qt 对齐——中文输入走 IBus 协议,不依赖系统的 Qt 插件,见下文。不要把依赖装进 `base` 环境。

## 从源码运行

```bash
git clone <repo-url> Memo
cd Memo

mamba create -n memo -c conda-forge -y python=3.11 \
  pyside6 qt6-main platformdirs pynput pytest pyinstaller
mamba activate memo

python -m memo
```

当前仓库没有提交 `environment.yml`;依赖以 `pyproject.toml` 和上面的 mamba 命令为准。

## Linux 中文输入

Memo 通过 **IBus 协议**接入输入法,不使用系统的 fcitx5 Qt 插件。

原因是 Qt 对 QPA 插件要求 `QT_VERSION` **精确匹配**,连同一大版本都不行。打包后的程序自带一份 Qt,而发行版的 `libfcitx5platforminputcontextplugin.so` 是按系统 Qt 编译的,两者必然对不上:

```text
Ignoring QPA plugin due to mismatching Qt versions 396032 394240
... undefined symbol: QWindowSystemInterface::handleExtendedKeyEvent(...)
```

而 Qt 自带的 ibus 插件就在 bundle 内部,版本永远一致。fcitx5 通过 `ibusfrontend` 附加组件提供 IBus 服务——它占用 `org.freedesktop.IBus` 总线名,并写出和 `ibus-daemon` 相同的地址文件。所以让 Qt 走 ibus,实际接到的仍然是 fcitx5。

这里有个坑。Qt 的 ibus 插件在建立任何连接之前,会先检查 **`ibus-daemon` 可执行文件是否在 `PATH` 上**:

```cpp
valid = !QStandardPaths::findExecutable("ibus-daemon", {}).isEmpty();
if (!valid)
    return;
```

只装了 fcitx5 的桌面上没有这个文件,插件会静默自我禁用,Qt 转而回退到 compose 上下文——没有预编辑、没有候选词框。设置 `IBUS_USE_PORTAL` 可以走 portal 分支跳过该检查,对端服务名换成 `org.freedesktop.portal.IBus`,这个名字同样由 fcitx5 的 ibusfrontend 持有。

启动时 `memo/core/input_method.py` 就做这两件事:如果 `QT_IM_MODULE` 是 `fcitx`/`fcitx5`,且检测到有进程正在提供 IBus 服务(读 `~/.config/ibus/bus/` 下的地址文件并确认其中记录的 PID 仍存活),把 `QT_IM_MODULE` 改写为 `ibus`;若 `ibus-daemon` 不在 `PATH` 上,再补设 `IBUS_USE_PORTAL=1`。检测不到 IBus 服务就原样放行,用户显式设过的 `IBUS_USE_PORTAL` 也不会被覆盖。

因此:

- 构建机不需要安装 fcitx5,也不需要 Qt6 的 fcitx5 插件
- 构建机的 Qt 版本和用户桌面的 Qt 版本无关
- 用户侧只需要 fcitx5(ibusfrontend 默认开启)或 ibus 正在运行

排查时可以看插件实际加载情况:

```bash
QT_LOGGING_RULES="qt.qpa.input.methods=true" ./dist/Memo
```

连接成功时会看到这两行:

```text
qt.qpa.input.methods: use IBus portal
qt.qpa.input.methods: >>>> bus connected!
```

只有 `socketWatcher.addPath` 而没有 `bus connected!`,说明插件自我禁用了——通常是 `IBUS_USE_PORTAL` 没生效。

## 测试

```bash
mamba run -n memo pytest -q
```

测试覆盖数据库、设置、开机自启、全局快捷键导入、图标、打包规则,以及新建待办对话框和标签右键菜单。

## 打包

PyInstaller 不能跨平台打包,需要在目标平台运行对应脚本。

Linux:

```bash
./scripts/build.sh
./dist/Memo
```

Windows:

```powershell
scripts\build.bat
dist\Memo.exe
```

打包配置在 `Memo.spec` 中。它会过滤未使用的 Qt 模块、QML、QtWebEngine、多媒体等内容,保留 QWidget、系统托盘、平台插件、输入法插件和热键后端所需依赖。

## 数据位置

Memo 使用 `platformdirs.user_data_dir("Memo", appauthor=False)` 决定数据目录,并支持用 `MEMO_DATA_DIR` 覆盖。

| 平台 | 默认位置 |
| --- | --- |
| Linux | `~/.local/share/Memo/` |
| Windows | 通常为 `%LOCALAPPDATA%\Memo\` |

目录内主要文件:

- `memo.db`:SQLite 数据库
- `settings.json`:窗口状态、筛选、快捷键、置顶、自启等偏好

## 开机自启

- Linux:`$XDG_CONFIG_HOME/autostart/memo.desktop`,默认 `~/.config/autostart/memo.desktop`
- Windows:`HKCU\Software\Microsoft\Windows\CurrentVersion\Run`

## 项目结构

```text
memo/
├── app.py          # QApplication 启动、托盘、快捷键、单实例生命周期
├── __main__.py     # python -m memo 入口
├── core/           # 数据库、模型、设置、路径、自启、全局快捷键、单实例
├── resources/      # QSS 样式
└── ui/             # PySide6 界面组件
tests/              # pytest 测试
scripts/            # 打包脚本
Memo.spec           # PyInstaller 配置
pyproject.toml      # 包元数据和运行依赖
```
