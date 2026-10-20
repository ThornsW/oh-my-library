# Voice-to-Text 语音输入

版本：0.1.1（运行 `./run.sh --version` 或 `./voice-to-text --version` 查看）

按住说话 → 云端识别 → 文字自动粘贴到你绑定的终端窗口 → 可选自动回车。

适合在终端里用 Codex CLI、Claude CLI 等工具时用语音代替打字，识别以中文为主，也能识别夹在中文里的英文技术词，比如 Claude、Ubuntu、API。

也可以远程使用：比如用平板远程控制电脑、程序跑在虚拟机里，只要麦克风声音能一路转发进这台 Linux 就行。具体做法见下文「远程使用提示」。

## 适用环境与限制

| 项目 | 要求 |
|---|---|
| 系统 | **Ubuntu 22.10 及以上**（或其他使用 PipeWire、glibc 2.34 以上的 Linux 发行版） |
| 桌面会话 | **X11**：在 Ubuntu 登录界面点右下角齿轮，选「Ubuntu on Xorg」 |
| Python | 系统自带的 Python 3.10 及以上，带 PyGObject 和 GTK 3（Ubuntu 桌面默认已装） |
| 系统命令 | `pw-record`、`pw-dump`（PipeWire）、`xdotool`、`xclip`、`xwininfo` |

- 不需要 conda 或虚拟环境：直接用系统自带的 Python 3（`/usr/bin/python3`）运行。依赖清单见 `requirements.txt`。
- **目前只支持 X11。** 在 Wayland 会话下，xdotool 没法往其他窗口发按键，所以程序检测到 Wayland 就会拒绝启动。Wayland 支持（ydotool / wtype 等方案）列在后续计划里。
- 暂不支持 Windows / macOS 原生运行。
- 识别必须联网，程序不带离线识别。

Ubuntu 桌面一般只缺 `xdotool` 和 `xclip`：

```bash
sudo apt install xdotool xclip
# 精简版系统上如果还缺，再装：pipewire-bin x11-utils python3-gi gir1.2-gtk-3.0
```

不需要 pip 安装任何 Python 包。

## 快速开始

**下载了编译好的 `voice-to-text`：**

1. 把它放进一个单独的文件夹。程序会在自己所在的文件夹里生成 `config.json`、`logs/` 等文件。
2. 加上可执行权限：在文件管理器里右键 →「属性」→ 勾选「允许作为程序执行」，或者运行 `chmod +x voice-to-text`。
3. 双击 `voice-to-text` 启动，然后从下面第 2 步开始设置。

**从源码开始：**

1. 生成单文件程序（改了代码后再运行一次）：
   ```bash
   ./build.sh
   ```
   然后在文件管理器里**双击 `voice-to-text`** 启动。也可以不生成，直接在终端运行 `./run.sh`。
2. 点「设置」→「识别服务」，填 API Key，点「测试连接」，看到 ✓ 后点「保存」。
3. 点「绑定窗口」，再点一下要输入文字的终端窗口。
4. 按住蓝色大按钮说话，松开后文字会出现在终端里。

## 启动方式

| 方式 | 怎么做 | 说明 |
|---|---|---|
| 单文件程序（推荐） | `./build.sh` 生成 `voice-to-text`，以后双击它 | 约 50 KB，不依赖终端，关掉终端也不会退出 |
| 从源码运行 | `./run.sh` | 适合改代码时用；关掉启动它的终端，程序也会退出 |

- 单文件程序里包含两部分：一个用 gcc 编译的小启动器，后面附带打包好的 Python 代码（zip）。运行时用系统自带的 Python（`/usr/bin/python3`）和 GTK，所以文件很小。要换 Python 就设置环境变量 `VTT_PYTHON`。
- 程序只会运行一份。已经在运行时再双击，不会开第二个，而是把已有的窗口切到前面。
- 两种方式共用同一份 `config.json`，配置文件都放在程序所在目录。单文件程序可以单独复制到别的目录用，它会在新目录里另建一份配置。
- 单文件程序支持和 `run.sh` 一样的诊断参数，比如 `./voice-to-text --test-asr test.wav`。

## 使用说明

- **按住说话**：按住按钮说话，松开就结束录音。
- **点一下开始、再点一下结束**：按下不到 0.4 秒就松开，会进入点按模式。有些远程软件会把触屏长按变成右键单击，这时候就用点按模式。按钮会提示当前处于哪种模式。
- **松手后继续录 1 秒**：避免最后一个字被截掉。收尾期间按钮已经可以再按，下一句可以马上开始说。时长在「设置 → 录音 → 松手后继续录音」里调，设为 0 就关闭。录到最长时间自动结束时，不会再多录这 1 秒。
- **主窗口和悬浮窗都能用。** 悬浮窗总在最前面，而且不会抢走终端的键盘焦点；点 ✕ 关闭，在主窗口点「悬浮窗」可以重新打开。
- **自动粘贴**：识别完直接粘贴到目标窗口。关闭后，识别结果放进编辑框，改好后点「发送」，或者点「仅复制」只复制到剪贴板。
- **自动回车**：粘贴后再按一次回车提交。关闭后，可以先在终端里检查文字，再点主窗口的「↵ 回车」提交。
- **目标窗口**有两种方式（在「设置 → 投递」里选）：
  - 固定窗口（默认）：用「绑定窗口」指定一个窗口，以后都发到这里。
  - 跟随最后使用的窗口：发到你最后点过的那个非本程序窗口。
- **目标是 VS Code 这类多面板程序时**：程序只能指定发到哪个窗口，没法指定发到窗口里的哪个面板。文字会贴到这个窗口里当前有光标的地方，所以要先在终端面板里点一下，别让光标停在编辑器里。
- **防止发错位置**：如果识别完成时你正在用别的窗口（既不是本程序，也不是目标窗口），程序不会自动发送。文字会以「待发送」状态留在历史里。粘贴之后、按回车之前，如果焦点变了，程序也不会按回车。
- **连续说多句**：识别可以同时进行，但发送严格按说话的顺序，每句只自动发送一次。失败或被拦下的句子留在历史里，可以点「发送选中」「复制」「重新识别」。退出程序时还没发送的文字存在 `cache/pending.json`，下次启动会自动恢复。

### 状态和报错

状态条按颜色显示当前状态：空闲（灰）、录音中（红，显示时长和音量）、识别中或发送中（蓝）、成功（绿）、待发送或警告（黄）、失败（红）。

报错的格式是 `[阶段] 原因`，阶段有这几种：配置、录音、识别、找窗口、切焦点、剪贴板、粘贴、回车。在历史里选中一条失败记录，下方会显示技术细节。所有显示和日志都会先去掉 API Key、`Bearer` 令牌和音频数据。

常见的报错：

| 报错 | 处理 |
|---|---|
| `[录音] 没有录到声音` | 检查麦克风是否开启、系统默认录音设备是否正确；远程桌面或虚拟机要确认声音已转发进来（见「远程使用提示」） |
| `[识别] HTTP 401` | API Key 填错或没填 |
| `[识别] HTTP 404` | 接口地址、模型名或接口类型不对 |
| `[切焦点] 当前前台是「…」` | 识别完成时你在用别的窗口，文字已保留，点「发送选中」 |
| `[找窗口] 绑定的窗口已关闭` | 重新点「绑定窗口」 |

## 识别服务配置

在「设置 → 识别服务」里可以添加多个服务，每个服务填这几项：名称、接口类型、接口地址、模型、API Key、附加参数（JSON，会合并进请求体）。

**换模型：** 接口类型相同的模型，只改「模型」就行，不需要写后端。不同的接口类型需要程序里有对应的适配代码。目前支持 3 种：

| 接口类型 | 请求地址 | 适用 |
|---|---|---|
| OpenAI 兼容 · 聊天音频 | `{地址}/chat/completions`，音频以 base64 放在 `input_audio` | 千问 `qwen3-asr-flash`（默认），其他兼容这种格式的服务 |
| OpenAI 标准转写 | `{地址}/audio/transcriptions`，multipart 上传文件 | OpenAI Whisper、Groq、硅基流动、本地 whisper 服务等 |
| DashScope 原生 · 同步 | `{地址}/services/aigc/multimodal-generation/generation` | 只提供 DashScope 原生接口的同步识别模型 |

默认预设（不含 Key）：

- 千问 OpenAI 兼容：地址 `https://maas.qianwenaiapi.com/compatible-mode/v1`，模型 `qwen3-asr-flash`
- 千问 DashScope 原生：地址 `https://maas.qianwenaiapi.com/api/v1`
- OpenAI Whisper：地址 `https://api.openai.com/v1`，模型 `whisper-1`

**不支持的模型类型：**

- 名字带 `-filetrans` 的异步文件转写模型，比如 `qwen-audio-3.1-asr-flash-filetrans`、`fun-asr`。它们要求先把音频放到公网 URL，再轮询结果，不适合按住说话。
- 名字带 `-realtime`、`-streaming`、`-message` 的实时 WebSocket 模型。这些列在后续计划里。

**音频编码**（只对「聊天音频」类型有效）：千问 / DashScope 用 `data URI`；OpenAI 官方的音频聊天模型用「纯 base64 + format」。

**提高英文技术词的识别率：**

- 「识别 → 热词 / 上下文」：填常用的词，比如 Codex、Claude Code、Ubuntu、API。这些词会作为上下文传给服务（聊天音频和原生接口放进 system 消息，标准转写放进 `prompt`）。
- 「识别 → 替换规则」：每行一条 `错词 => 正确词`，识别完自动替换，不区分大小写。适合修正固定会认错的词，例如 `cloud code => Claude Code`。
- 「语言」：中英混说时建议选「自动检测」。

## 远程使用提示

远程软件或虚拟机的每一层，都要把麦克风声音转发给下一层。下面以「平板 → UU远程 → Windows → VMware → Ubuntu」为例，换成其他软件时思路相同：

1. 用 UU 连上电脑后，在 Windows「设置 → 系统 → 声音 → 输入」里，把 UU 远程麦克风设为默认录音设备。说话时看看音量条有没有跳动。
2. VMware 菜单「虚拟机 → 可移动设备 → 声卡」保持「已连接」。
3. 在 Ubuntu 里先跑一下 `./run.sh --record 5 --out test.wav`，边录边说话，看输出的最大音量。-50 dB 以上才算录到了声音。
4. 程序会写入 Ubuntu 的剪贴板，VMware Tools 会把它同步到 Windows 的剪贴板。

## 会产生哪些文件

运行时生成的文件都在**程序所在目录**。如果程序目录不能写，就放到 `~/.config/voice-to-text/`，界面上会提示。也可以用 `--config-dir` 或环境变量 `VTT_CONFIG_DIR` 指定位置。

| 文件 | 内容 | 什么时候生成 |
|---|---|---|
| `config.json` | 全部设置，**API Key 是明文**（文件权限 600） | 第一次启动 |
| `logs/vtt-YYYY-MM-DD.log` | 运行日志，按启动日期分文件，不含 Key 和音频 | 每次启动 |
| `cache/pending.json` | 还没发送的文字和编辑框内容 | 有未发送内容时生成，清空后自动删除 |

- `config.json`、`logs/`、`cache/` 已写进 `.gitignore`，**不要把 `config.json` 提交到仓库**。仓库里只放不含 Key 的 `config.example.json`。
- `run.sh` 用 `python3 -B` 启动，不会生成 `__pycache__`。
- 录音只存在内存里，发给你配置的识别服务，不写入磁盘。用 `--record` 诊断时才会写出你指定的 wav 文件。
- 程序不会在 `~/.config`、`~/.cache`、`~/.local/share` 下生成文件（用了上面的备用目录时例外）。
- 构建（`./build.sh`）只生成一个文件 `voice-to-text`。构建时的临时文件 `voice-to-text.tmp` 在最后一步会被改名成 `voice-to-text`，不会留下来。不产生其他缓存，也不需要安装任何东西（用系统自带的 gcc 和 Python）。`voice-to-text` 已写进 `.gitignore`。
- 日志不会自动清理，需要时手动删除 `logs/` 里的旧文件。

## 体积与资源占用

- 程序本身：源码约 160 KB；单文件程序约 50 KB。
- 内存：空闲时独占约 33 MB（PSS）。`ps` 显示的 RSS 约 83 MB，其中大部分是和桌面上其他程序共用的 GTK 库。
- 录音时：再加一个约 9 MB 的 `pw-record` 进程，录音数据每分钟约 2 MB，只放在内存里。
- CPU：空闲时为 0%。

## 诊断命令

```bash
./run.sh --list-devices                     # 列出录音设备
./run.sh --record 5 --out test.wav          # 录 5 秒并显示最大音量
./run.sh --test-asr test.wav                # 用当前服务识别一个 wav
./run.sh --test-asr test.wav --provider "千问 DashScope 原生（同步）"
./run.sh --test-deliver "测试文字" --enter   # 发到已绑定的窗口并回车（也可用 --window <id>）
```

## 开发

```bash
python3 -B -m unittest discover -s tests    # 纯逻辑测试，不需要麦克风、网络和桌面
```

代码结构：

```
build.sh          生成单文件程序 voice-to-text
launcher/         单文件程序的 C 启动器
run.sh            从源码启动
voice_to_text/
  audio.py        录音（pw-record）、音量、WAV
  asr.py          3 种识别接口的请求和解析
  deliver.py      剪贴板（xclip）+ 切窗口、按键（xdotool）
  pipeline.py     录音 → 识别 → 按序发送；未发送内容的保存和恢复
  postprocess.py  文字整理与替换规则
  config.py       config.json 读写和默认值
  log.py          日志与脱敏
  ui/             GTK 3 界面：主窗口、悬浮窗、按住说话按钮、设置
```

## 后续计划

- Wayland 支持
- 实时流式识别（边说边出字）
- Windows 原生版本

## 许可

MIT
