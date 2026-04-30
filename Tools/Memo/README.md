# Memo

跨平台桌面待办 / 笔记应用。常驻系统托盘,左侧标签栏 + 右侧待办列表 + 详情面板,笔记支持 Markdown,数据本地 SQLite。兼容 Windows 与 Ubuntu。

## 功能

- 主窗口 + 系统托盘常驻;关闭主窗口仅隐藏到托盘
- 待办字段:标题、Markdown 笔记、截止日期、优先级、标签(多对多)、子任务清单
- 列表筛选:全部 / 未完成 / 已完成;按标签;模糊搜索标题与笔记
- 笔记编辑/预览双标签,Markdown 原生渲染
- 可切换的窗口置顶
- 可开关的开机自启(Linux 写 `~/.config/autostart/memo.desktop`,Windows 写 `HKCU\Run`)
- 可自定义全局快捷键(默认 `Ctrl+Shift+M`)切换主窗口显示/隐藏
- 数据存放系统标准用户数据目录,SQLite 单文件易备份

## 从源码运行(开发)

依赖 [`miniforge`](https://github.com/conda-forge/miniforge):

```bash
mamba create -n memo python=3.12
mamba activate memo
mamba install -c conda-forge pyside6 platformdirs pynput pytest qtawesome pyinstaller

git clone <your-repo-url> Memo
cd Memo
python -m memo
```

测试:`pytest`

## 打包成单可执行文件

PyInstaller 不支持跨平台打包,需要在 **目标系统** 上运行打包脚本。

### Linux / macOS

```bash
./scripts/build.sh
# 产物: dist/Memo  (≈117 MB)
./dist/Memo            # 双击或命令行皆可
```

### Windows

```powershell
scripts\build.bat
:: 产物: dist\Memo.exe
```

注:`build/` 与 `dist/` 已加入 `.gitignore`,二进制建议通过 GitHub Releases 分发,不直接推到主分支。

## 数据位置

| 平台 | 路径 |
| --- | --- |
| Linux | `~/.local/share/Memo/` |
| Windows | `%APPDATA%\Memo\` |

文件:`memo.db`(SQLite)、`settings.json`(偏好)。删除目录即重置所有数据。

## 项目结构

```
memo/
├── core/        # 数据层(paths/db/models/settings/autostart/hotkey)
├── ui/          # PySide6 控件(主窗口/标签栏/列表/详情/子任务/设置)
├── app.py       # QApplication 启动入口
└── __main__.py  # python -m memo 入口
tests/           # pytest:db / settings / autostart
scripts/         # 打包脚本
Memo.spec        # PyInstaller 规格
```
