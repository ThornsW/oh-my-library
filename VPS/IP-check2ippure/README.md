# IP-check2ippure

批量检测**任意机场订阅**所有节点的出口 IP 质量：逐个节点经 [IPPure](https://ippure.com/) 公共 API（`https://my.ippure.com/v1/info`）查询，汇总成按风险分排序的报表（风险分 / 是否原生家宽 / 是否机房 / ASN / 地理位置 / 延迟）。

## 工作原理

IPPure 返回的是「发起请求那条连接的出口 IP」的信息。本工具在本机启动一个临时 [mihomo](https://github.com/MetaCubeX/mihomo)（clash-meta），把订阅里每个节点都纳入一个选择器组，然后逐个切换节点、经 mihomo 代理去查 IPPure，最后汇总。

## 运行要求

- **平台**：Linux / macOS（amd64 或 arm64，自动匹配对应 mihomo 构建）；原生 Windows 请在 WSL 下运行。
- **Python 3.10+**，仅用标准库，**无需 `pip install` 任何包**。
- 首次运行会自动从 GitHub Releases 下载 mihomo（clash-meta）静态二进制到 `bin/`（之后复用并校验 SHA256）。
- 联网：需能访问 GitHub（下载 mihomo）以及各节点服务器。

## ⚠️ 运行前必须关闭本机的透明/系统代理

> 下文以 OpenWrt 上的 **PassWall** 为例；你用别的透明代理（OpenClash、sing-box、TUN 模式等）同理，脚本里的提示文案写作 “PassWall”，按你的实际情况操作即可。
>
> 如果你本机**没有**任何透明/系统代理（本来就是直连上网），脚本停下提示时直接回车继续即可。

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
cd IP-check2ippure
python3 check_airport.py '<订阅URL>' --name 机场名
```

> **订阅 URL 一定要用单引号包起来**：很多订阅链接带 `&`，不加引号会被 shell 当成后台符拆断命令。

选项：

- `--name LABEL` 结果文件名标签（默认 `airport`）
- `--timeout SEC` 单节点 IPPure 请求超时秒数（默认 8）
- `--gap SEC` 节点间间隔，礼貌限流（默认 0.3）
- `--limit N` 只测前 N 个节点（调试用，0=全部）
- `--keep-config` 保留 `run/` 下的临时配置与日志（默认清理）

报表打印到终端，并写入 `results/<机场名>-<时间戳>.csv` 与 `.md`。

## 字段含义

| 列 | 含义 |
|---|---|
| 风险分 | IPPure fraudScore，0–100，越低越干净 |
| 原生 | 是否住宅/家宽 IP（IPPure isResidential） |
| 机房? | 启发式：非住宅且 ASN/组织名命中常见云厂商关键词 |
| 延迟ms | mihomo 对该节点的握手时延 |
| 状态 | ok / timeout / fail / ratelimit |

## 足迹（无环境污染）

全部落在本目录内：

- `bin/mihomo`：自动下载的官方静态二进制（首次运行下载并固定 SHA256）
- `run/`：运行时生成的配置与日志（默认用完清理）
- `results/`：报表（含真实节点信息，已在 `.gitignore` 中，不会被提交/公开）

不向 `~/.config/mihomo` 写任何东西（用 `-d ./run` 钉死工作目录、配置不含 GEOIP 规则）。编排脚本**纯 Python 标准库**，任意 Python 3.10+ 解释器均可运行。

## 测试

```bash
cd IP-check2ippure
python3 -m unittest discover -s tests -t . -v
```

## 卸载

```bash
rm -rf IP-check2ippure
```

不留任何痕迹。
