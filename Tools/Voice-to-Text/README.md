# Voice-to-Text 语音输入

版本：0.1.1（运行 `./voice-to-text --version` 查看）

按住说话，云端识别后把文字粘贴到绑定的终端窗口，可选自动回车。适合在终端里用 Codex CLI、Claude CLI 时代替打字。以中文为主，也能识别夹在中文里的英文技术词。

## 运行环境

- Ubuntu 22.10+，或其他用 PipeWire、glibc 2.34+ 的 Linux
- **X11 会话**：在登录界面右下角的齿轮里选「Ubuntu on Xorg」。Wayland 下无法向其他窗口发按键，程序会拒绝启动
- 系统自带的 Python 3.10+ 和 GTK 3（Ubuntu 桌面默认就有），不需要 conda，也不用 pip 装包
- 识别需要联网；暂不支持 Windows / macOS

Ubuntu 桌面一般只需补装：

```bash
sudo apt install xdotool xclip
# 精简版系统还可能缺：pipewire-bin x11-utils python3-gi gir1.2-gtk-3.0
```

## 安装与启动

```bash
./build.sh    # 生成单文件程序 voice-to-text（约 50 KB），以后双击它启动
./run.sh      # 或者直接从源码运行，关掉终端程序也会退出
```

已有编译好的 `voice-to-text`：放进一个单独的文件夹，`chmod +x voice-to-text` 后双击启动。设置和日志都生成在程序所在目录。

程序只运行一份，再次启动会把已有窗口切到前面。

## 快速上手

1. 「设置 → 识别服务」填 API Key，点「测试连接」，看到 ✓ 后保存
2. 点「绑定窗口」，再点一下要输入的终端窗口
3. 按住蓝色大按钮说话，松开后文字出现在终端里

## 使用要点

- **按住说话**，松开结束。按下不到 0.4 秒就松开会进入**点按模式**（点一下开始、再点一下结束），适合会把长按变成右键的远程软件
- 松手后默认再录 1 秒，防止最后一个字被截掉，可在「设置 → 录音」里调，设为 0 即关闭
- **悬浮窗**总在最前面，而且不抢键盘焦点
- 关掉**自动粘贴**后，结果先进编辑框，改好再点「发送」或「仅复制」；关掉**自动回车**后，可以检查完再点「↵ 回车」
- **目标窗口**可以固定绑定（默认），也可以跟随你最后使用的窗口。VS Code 这类多面板程序只能定位到窗口，文字会落在当前光标处，记得先点一下终端面板
- **防误发**：识别完成时你在用别的窗口，文字不会自动发出，而是以「待发送」留在历史里。连续说多句时按说话顺序发送。退出时没发出的文字存进 `cache/pending.json`，下次启动自动恢复

## 识别服务

「设置 → 识别服务」里可以添加多个服务。接口类型相同的模型只需改「模型」。支持 3 种接口：

| 接口类型 | 请求地址 | 适用 |
|---|---|---|
| OpenAI 兼容 · 聊天音频 | `{地址}/chat/completions` | 千问 `qwen3-asr-flash`（默认）等 |
| OpenAI 标准转写 | `{地址}/audio/transcriptions` | OpenAI Whisper、Groq、硅基流动、本地 whisper 服务等 |
| DashScope 原生 · 同步 | `{地址}/services/aigc/multimodal-generation/generation` | 只提供 DashScope 原生接口的同步模型 |

- 不支持异步文件转写模型（名字带 `-filetrans`）和实时 WebSocket 模型（带 `-realtime`、`-streaming`）
- 「音频编码」只对聊天音频类型有效：千问 / DashScope 用 `data URI`，OpenAI 官方音频聊天模型用「纯 base64 + format」
- 英文技术词认不准时：在「热词 / 上下文」里填常用词；用「替换规则」（每行 `错词 => 正确词`）修正固定认错的词；中英混说时语言选「自动检测」

## 常见报错

报错格式是 `[阶段] 原因`，在历史里选中失败的记录能看到技术细节。

| 报错 | 处理 |
|---|---|
| `[录音] 没有录到声音` | 检查麦克风和系统默认录音设备；远程桌面或虚拟机里要确认声音已转发进来 |
| `[识别] HTTP 401` | API Key 填错或没填 |
| `[识别] HTTP 404` | 接口地址、模型名或接口类型不对 |
| `[切焦点] 当前前台是「…」` | 识别完成时你在用别的窗口，文字已保留，点「发送选中」 |
| `[找窗口] 绑定的窗口已关闭` | 重新「绑定窗口」 |

**远程使用**（比如平板 → 远程软件 → Windows → 虚拟机 → Ubuntu）：每一层都要把麦克风转发给下一层。先运行 `./run.sh --record 5 --out test.wav` 边录边说，最大音量在 -50 dB 以上才算录到了声音。

## 文件位置

都在程序所在目录。目录不可写时改用 `~/.config/voice-to-text/`；也可以用 `--config-dir` 或环境变量 `VTT_CONFIG_DIR` 指定。

- `config.json`：全部设置，**API Key 明文保存**（权限 600），不要提交到仓库。仓库里只放不含 Key 的 `config.example.json`
- `logs/`：运行日志，不含 Key 和音频，不会自动清理
- `cache/pending.json`：还没发出的文字

录音只在内存里，发给你配置的识别服务，不写入磁盘。

## 诊断命令

```bash
./run.sh --list-devices                     # 列出录音设备
./run.sh --record 5 --out test.wav          # 录 5 秒并显示最大音量
./run.sh --test-asr test.wav                # 用当前服务识别一个 wav
./run.sh --test-deliver "测试文字" --enter   # 发到已绑定的窗口并回车
```

单文件程序 `voice-to-text` 支持同样的参数。

## 开发

```bash
python3 -B -m unittest discover -s tests    # 不需要麦克风、网络和桌面
```

改完代码重新运行 `./build.sh`。要换 Python 解释器就设环境变量 `VTT_PYTHON`。

## 许可

MIT
