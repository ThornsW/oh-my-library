# Memo

版本：0.1.1

本地桌面待办 + Markdown 笔记。PySide6 界面，SQLite 保存数据，常驻系统托盘，支持 Linux 和 Windows。

## 功能

- 三栏界面：标签栏、待办列表、详情编辑器
- 待办可以有笔记、截止日期、优先级、标签、子任务
- 按未完成 / 全部 / 已完成筛选，按标签过滤，搜索标题和笔记
- 在标签上右键，可以直接在这个标签下新建待办
- Markdown 笔记编辑与预览
- 关闭窗口时隐藏到托盘；支持置顶、开机自启，以及用全局快捷键显示 / 隐藏
- 数据只存在本地，不联网

## 运行环境

- Python 3.11+；本仓库默认用 miniforge 的 `GeneralDev` 环境
- 依赖见 `requirements.txt`（运行）和 `requirements-dev.txt`（测试、打包）
- 桌面要有系统托盘

## 安装与运行

在 `Tools/Memo` 目录下：

```bash
# 用 GeneralDev（依赖已装好）
mamba activate GeneralDev
pip install -e . --no-deps
python -m memo

# 用其他环境：先装依赖
pip install -r requirements-dev.txt
pip install -e .
```

`pip install -e .` 不能省：开机自启的启动命令是 `python -m memo`，不装的话登录后会找不到程序。

## 已知限制

- **必须有系统托盘**，没有时程序会提示并退出。原版 GNOME（如 Fedora）要先装 AppIndicator 扩展
- **Linux 下全局快捷键只在 X11 可用**。Wayland 下可以在系统设置里给 `python -m memo` 绑一个快捷键，再次启动就会把已有窗口唤到前面
- Windows 打包脚本还没在真机上验证过，遇到问题欢迎反馈

## Linux 中文输入

Memo 通过 IBus 协议接入输入法，桌面上运行着 fcitx5（默认开启 ibusfrontend）或 ibus 就能用，不依赖系统的 Qt 输入法插件。

输入法不工作时，查看插件的加载日志：

```bash
QT_LOGGING_RULES="qt.qpa.input.methods=true" python -m memo
```

正常时会看到 `>>>> bus connected!`。

## 数据位置

默认目录如下，可以用环境变量 `MEMO_DATA_DIR` 改掉：

- Linux：`~/.local/share/Memo/`
- Windows：通常是 `%LOCALAPPDATA%\Memo\`

里面是 `memo.db`（数据库）和 `settings.json`（偏好设置）。开机自启项写在 `~/.config/autostart/memo.desktop`（Linux）或注册表 `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`（Windows）。

## 测试与打包

```bash
mamba run -n GeneralDev pytest -q      # 在本目录运行

./scripts/build.sh && ./dist/Memo      # Linux 打包并运行
scripts\build.bat                      # Windows 打包，生成 dist\Memo.exe
```

PyInstaller 不能跨平台，要在目标系统上打包。打包配置在 `Memo.spec`。

## 许可

MIT
