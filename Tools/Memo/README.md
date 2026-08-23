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
- Python 3.11
- PySide6 6.4.x
- Linux 打包中文输入:构建机需要安装 `fcitx5` 和 Qt6 fcitx5 输入法插件
- Windows 全局快捷键:依赖 `pynput`

Python 和 PySide6 版本被固定在 3.11 / 6.4.x,是为了匹配 Ubuntu 24.04 的系统 Qt 6.4.2 和 `fcitx5-frontend-qt6` 插件 ABI。不要把依赖装进 `base` 环境。

## 从源码运行

```bash
git clone <repo-url> Memo
cd Memo

mamba create -n memo python=3.11 -y
mamba activate memo
mamba install -c conda-forge -y 'pyside6=6.4.*' 'qt6-main=6.4.*' \
  platformdirs pynput pytest pyinstaller

python -m memo
```

当前仓库没有提交 `environment.yml`;依赖以 `pyproject.toml` 和上面的 mamba 命令为准。

## Linux 中文输入

源码运行时,conda Qt 需要能加载系统的 fcitx5 Qt6 输入法插件。先确认系统里有插件:

```bash
test -f /usr/lib/x86_64-linux-gnu/qt6/plugins/platforminputcontexts/libfcitx5platforminputcontextplugin.so
```

如果源码运行无法输入中文,把系统插件链接到 conda Qt 的插件目录:

```bash
SP=$(mamba run -n memo python -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')
QT_INPUT_DIR="$(dirname "$SP")/qt6/plugins/platforminputcontexts"
mkdir -p "$QT_INPUT_DIR"
ln -sfn /usr/lib/x86_64-linux-gnu/qt6/plugins/platforminputcontexts/libfcitx5platforminputcontextplugin.so \
  "$QT_INPUT_DIR/libfcitx5platforminputcontextplugin.so"
```

打包时,`Memo.spec` 会在 Linux 上自动把构建机的 `libfcitx5platforminputcontextplugin.so` 放进 bundle,并保留 ibus 插件。下载者仍需要自己的系统正在运行 fcitx5 和中文输入引擎。

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
