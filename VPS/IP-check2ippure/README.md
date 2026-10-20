# IP-check2ippure

版本：0.1.0（运行 `python3 check_airport.py --version` 查看）

批量检测机场订阅里每个节点的出口 IP 质量。程序在本机临时启动一个 [mihomo](https://github.com/MetaCubeX/mihomo)，逐个切换节点去查询 [IPPure](https://ippure.com/)，最后汇总成按风险分排序的报表，包含风险分、是否原生家宽、是否机房、ASN、地理位置和延迟。

## 运行环境

- Linux / macOS / Windows，amd64 或 arm64
- Python 3.10+，只用标准库，不用装包；本仓库默认用 `GeneralDev` 环境
- 首次运行会自动从 GitHub 下载 mihomo 到 `bin/`，下载不了时见「手动准备 mihomo」

## 用法

```bash
cd VPS/IP-check2ippure
python3 check_airport.py --name 机场名
```

**运行前要关掉本机的透明代理和系统代理**，比如 PassWall、OpenClash、TUN 模式、系统代理。原因是很多机场不给代理 IP 下发订阅，而且测试时也不该再套一层代理。脚本下载完 mihomo 后会停下来提醒你关代理，跑完再提醒你打开。本来就是直连上网的，直接回车或加 `--yes` 跳过。

订阅 URL 相当于密码，程序按下面的顺序读取它。推荐用后三种，不会留在 shell 历史里：

1. 命令行参数：`python3 check_airport.py '<订阅URL>' --name 机场名`。一定要加引号，Windows cmd 里用双引号
2. 环境变量 `IPPURE_SUB_URL`
3. 本目录的 `.env`：`cp .env.example .env` 后填写
4. 以上都没有时，运行后提示你粘贴，输入时不显示

报表打印在终端里，同时写入 `results/<机场名>-<时间戳>.csv` 和 `.md`。Windows 上请把 `python3` 换成 `python` 或 `py`。

### 选项

| 选项 | 说明 |
|---|---|
| `--name LABEL` | 结果文件名标签，默认 `airport` |
| `--timeout SEC` | 单个节点的请求超时，默认 8 秒 |
| `--gap SEC` | 节点之间的间隔，默认 0.3 秒 |
| `--limit N` | 只测前 N 个节点，0 表示全部 |
| `--ua UA` | 拉取订阅用的 User-Agent，默认 `mihomo` |
| `--mihomo PATH` | 用本地的 mihomo，不再下载；也可以设环境变量 `MIHOMO_BIN` |
| `-y`, `--yes` | 不等回车确认 |
| `--keep-config` | 保留 `run/` 下的临时配置和日志 |

### 报表字段

| 列 | 含义 |
|---|---|
| 风险分 | IPPure 的 fraudScore，0–100，越低越干净 |
| 原生 | 是否住宅 / 家宽 IP |
| 机房? | 非住宅，且 ASN 或组织名命中了云厂商关键词（关键词表在 `core/classify.py`，可以自己改） |
| 延迟ms | mihomo 到节点的握手时延 |
| 状态 | ok / timeout / fail / ratelimit |

## 手动准备 mihomo

1. 从 [mihomo Releases](https://github.com/MetaCubeX/mihomo/releases) 下载对应平台的包，amd64 推荐 `-compatible` 版
2. 解压出可执行文件，Linux / macOS 还要 `chmod +x`
3. 运行时加 `--mihomo /path/to/mihomo`，或者设环境变量 `MIHOMO_BIN`

## 故障排查

| 现象 | 处理 |
|---|---|
| 下载 mihomo 失败 | 下载这一步可以开着代理跑，或者手动准备 mihomo |
| `60s 内订阅节点列表为空` | 代理没关、订阅失效，或者机场按 UA 下发订阅（试试 `--ua clash.meta`） |
| 很多节点是 `ratelimit` | 被 IPPure 限流了，把 `--gap` 调大，比如 `--gap 1` |
| 杀毒软件拦截 mihomo | 加白名单，或用 `--mihomo` 指定自己下载、核对过的文件 |

IPPure 是免费的公共服务：请保持默认间隔，不要把 `--gap` 调到 0，也不要同时跑多个实例。

## 文件与卸载

所有文件都在本目录里，不会写入 `~/.config/mihomo`：

- `bin/`：mihomo
- `run/`：运行时的配置，用完自动清理
- `results/`：报表，含真实节点信息，已被 `.gitignore` 忽略

卸载时删掉整个目录即可。

## 测试

```bash
python3 -m unittest discover -s tests -t . -v    # 全部离线，不联网也不动代理
```
