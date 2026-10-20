# IP-check2ippure

版本：0.1.0（运行 `python3 check_airport.py --version` 查看）

批量检测**任意机场订阅**所有节点的出口 IP 质量：逐个节点经 [IPPure](https://ippure.com/) 公共 API（`https://my.ippure.com/v1/info`）查询，汇总成按风险分排序的报表（风险分 / 是否原生家宽 / 是否机房 / ASN / 地理位置 / 延迟）。

## 工作原理

IPPure 返回的是「发起请求那条连接的出口 IP」的信息。本工具在本机启动一个临时 [mihomo](https://github.com/MetaCubeX/mihomo)（clash-meta），把订阅里每个节点都纳入一个选择器组，然后逐个切换节点、经 mihomo 代理去查 IPPure，最后汇总。

## 运行要求

- **平台**：Linux / macOS / Windows（amd64 或 arm64，自动匹配并下载对应的 mihomo 构建）。
- **Python 3.10+**，仅用标准库，**无需 `pip install` 任何包**（见 `requirements.txt`）。本仓库默认用 miniforge 的 `GeneralDev` 环境（Python 3.12），其他 3.10+ 解释器也可以。
- 首次运行会自动从 GitHub Releases 下载 mihomo（clash-meta）静态二进制到 `bin/`（之后复用并校验 SHA256）。下载不了时见下文「手动准备 mihomo」。
- 联网：需能访问 GitHub（下载 mihomo）以及各节点服务器。

## ⚠️ 运行前必须关闭本机的透明/系统代理

> 透明/系统代理指 OpenWrt 上的 PassWall、OpenClash，或者 sing-box、TUN 模式、Clash for Windows、Windows 系统代理等。脚本提示里统称「透明/系统代理」，按你的实际情况关闭即可。
>
> 如果你本机**没有**任何透明/系统代理（本来就是直连上网），脚本停下提示时直接回车，或者加 `--yes` 跳过这一步。

两个原因：

1. **拉取订阅时**：很多机场有「保护规则」，检测到请求来自代理/机房 IP 会拒绝下发订阅（返回「请关闭网络代理后再获取订阅」）。必须用你的真实家庭 IP 才拉得到节点。
2. **逐节点测试时**：若仍经透明代理，测试连接会被再套一层当前节点（代理套代理）——出口 IP 虽仍准确，但延迟翻倍、且依赖当前活动节点在线。

脚本流程（关代理在拉订阅之前）：

1. 准备 mihomo 二进制（这步可开着代理，便于从 GitHub 下载）。
2. **提示你手动关闭透明代理**，回车继续。
3. 关掉后才拉取订阅、再逐节点测试（全程无代理）。
4. 跑完提示你**重新打开代理**。

## 用法

```bash
cd VPS/IP-check2ippure
python3 check_airport.py --name 机场名
```

订阅 URL 相当于密码，按下面的顺序取，推荐用后两种，避免留在 shell 历史里：

1. 命令行参数：`python3 check_airport.py '<订阅URL>' --name 机场名`
2. 环境变量 `IPPURE_SUB_URL`
3. 本目录的 `.env` 文件：`cp .env.example .env` 后填写（`.env` 已在 `.gitignore` 中）。已经设置的环境变量优先，`.env` 只补空缺。
4. 以上都没有时，运行后提示粘贴，输入不显示

> **跨平台提示**：
> - 命令里的 `python3` 在 Windows 上请用 `python` 或 `py`。
> - 在命令行传订阅 URL 时**一定要加引号**（很多链接带 `&` 等特殊字符，不加会被 shell 拆断）：Linux / macOS / Windows PowerShell 用单引号 `'...'`；Windows **cmd.exe** 用双引号 `"..."`。

选项：

- `--name LABEL` 结果文件名标签（默认 `airport`）
- `--timeout SEC` 单节点 IPPure 请求超时秒数（默认 8）
- `--gap SEC` 节点间间隔，礼貌限流（默认 0.3）
- `--limit N` 只测前 N 个节点（调试用，0=全部）
- `--ua UA` 拉取订阅时的 User-Agent（默认 `mihomo`）
- `--mihomo PATH` 使用本地的 mihomo 可执行文件，不再自动下载（也可设环境变量 `MIHOMO_BIN`）
- `-y`, `--yes` 不等待回车确认（本机没有透明/系统代理，或已提前关闭时使用）
- `--keep-config` 保留 `run/` 下的临时配置与日志（默认清理）
- `--version` 显示版本号

报表打印到终端，并写入 `results/<机场名>-<时间戳>.csv` 与 `.md`。

## 字段含义

| 列 | 含义 |
|---|---|
| 风险分 | IPPure fraudScore，0–100，越低越干净 |
| 原生 | 是否住宅/家宽 IP（IPPure isResidential） |
| 机房? | 启发式：非住宅且 ASN/组织名命中常见云厂商关键词（关键词表在 `core/classify.py`，可自行增减） |
| 延迟ms | mihomo 对该节点的握手时延 |
| 状态 | ok / timeout / fail / ratelimit |

## 手动准备 mihomo

自动下载走的是 GitHub API，国内直连或触发 API 限流时可能失败。可以手动下载：

1. 到 [mihomo Releases](https://github.com/MetaCubeX/mihomo/releases) 下载对应平台的包：Linux / macOS 是 `mihomo-<系统>-<架构>-v<版本>.gz`（amd64 推荐 `-compatible` 版），Windows 是 `.zip`。
2. 解压出可执行文件（Linux / macOS 还要 `chmod +x`）。
3. 运行时用 `--mihomo /path/to/mihomo` 指定，或者设置环境变量 `MIHOMO_BIN`。

也可以把文件放到 `bin/mihomo`（Windows 是 `bin/mihomo.exe`），并在同目录写一个 `mihomo.sha256`，内容是它的 SHA256（Linux：`sha256sum bin/mihomo | cut -d' ' -f1 > bin/mihomo.sha256`）。缺这个文件时程序会重新下载。

## 故障排查

| 现象 | 处理 |
|---|---|
| 第 1 步下载 mihomo 失败 | 开着代理跑（这一步还不需要关代理），或按上一节手动准备 mihomo |
| `60s 内订阅节点列表为空` | ① 透明/系统代理没关；② 订阅 URL 失效；③ 机场按 UA 下发，试试 `--ua clash.meta` 或机场要求的 UA |
| 很多节点状态是 `ratelimit` | IPPure 限流了，把 `--gap` 调大（比如 `--gap 1`）后重试 |
| Windows 杀毒软件拦截 mihomo | mihomo 是 GitHub 上的官方构建；可以加白名单，或用 `--mihomo` 指定你自己下载、核对过的文件 |

## 礼貌使用

IPPure 是免费的公共服务。请保持串行检测和默认的节点间隔，不要把 `--gap` 调到 0，也不要同时跑多个实例。

## 足迹（无环境污染）

全部落在本目录内：

- `bin/mihomo`：自动下载的官方静态二进制（首次运行下载并固定 SHA256）
- `run/`：运行时生成的配置与日志（默认用完清理）
- `results/`：报表（含真实节点信息，已在 `.gitignore` 中，不会被提交/公开）

不向 `~/.config/mihomo` 写任何东西（用 `-d ./run` 钉死工作目录、配置不含 GEOIP 规则）。编排脚本**纯 Python 标准库**，任意 Python 3.10+ 解释器均可运行。

## 测试

```bash
cd VPS/IP-check2ippure
python3 -m unittest discover -s tests -t . -v
```

测试全部离线运行，不会联网、下载 mihomo 或改动代理设置。

## 卸载

删掉整个 `IP-check2ippure` 目录即可，不留任何痕迹。
