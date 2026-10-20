#!/usr/bin/env python3
"""IP-check2ippure：批量经 IPPure 检测机场节点出口 IP 质量。

用法：
  python check_airport.py [订阅URL] [--name 标签] [--timeout 8] [--gap 0.3] [--limit N]
                          [--ua UA] [--mihomo PATH] [--yes] [--keep-config] [--version]
"""
import argparse
import getpass
import os
import secrets
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from core import __version__                     # noqa: E402
from core.binary import ensure_mihomo            # noqa: E402
from core.config_gen import build_config, dump_config  # noqa: E402
from core.envfile import load_env_file           # noqa: E402
from core.mihomo import MihomoController         # noqa: E402
from core.netutil import find_free_port          # noqa: E402
from core.ippure import query_via_proxy, query_direct  # noqa: E402
from core.runner import run_checks               # noqa: E402
from core.report import sort_results, render_table, write_csv, write_markdown  # noqa: E402

BIN_DIR = os.path.join(HERE, "bin")
RUN_DIR = os.path.join(HERE, "run")
RESULTS_DIR = os.path.join(HERE, "results")
ENV_PATH = os.path.join(HERE, ".env")
SUB_ENV = "IPPURE_SUB_URL"
MIHOMO_ENV = "MIHOMO_BIN"


def _ts() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="批量经 IPPure 检测机场节点出口 IP 质量")
    ap.add_argument("sub_url", nargs="?", default=None,
                    help=f"机场订阅 URL；省略时依次读环境变量 {SUB_ENV}、本目录 .env，最后提示输入（不回显）")
    ap.add_argument("--name", default="airport", help="机场标签（用于结果文件名）")
    ap.add_argument("--timeout", type=float, default=8, help="单节点 IPPure 请求超时秒数")
    ap.add_argument("--gap", type=float, default=0.3, help="节点间间隔秒数（礼貌限流）")
    ap.add_argument("--limit", type=int, default=0, help="只测前 N 个节点（调试用，0=全部）")
    ap.add_argument("--ua", default="mihomo", help="拉取订阅时的 User-Agent（默认 mihomo）")
    ap.add_argument("--mihomo", metavar="PATH", default=os.environ.get(MIHOMO_ENV) or None,
                    help=f"使用本地 mihomo 可执行文件，不再自动下载（也可设环境变量 {MIHOMO_ENV}）")
    ap.add_argument("-y", "--yes", action="store_true",
                    help="不等待回车确认（本机没有透明/系统代理，或已提前关闭时使用）")
    ap.add_argument("--keep-config", action="store_true", help="保留 run/ 下生成的配置与日志")
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return ap


def resolve_sub_url(cli_value, environ=os.environ, prompt=getpass.getpass) -> str:
    """订阅 URL 优先级：命令行 > 环境变量（含 .env 补充的）> 交互输入。

    交互输入不回显，也不会留在 shell 历史里。
    """
    url = (cli_value or environ.get(SUB_ENV, "")).strip()
    if not url:
        url = prompt("请粘贴机场订阅 URL（输入不显示）：").strip()
    if not url:
        raise SystemExit("未提供订阅 URL")
    return url


def resolve_binary(path, bin_dir: str, ensure) -> str:
    """指定了本地 mihomo 就直接用，否则下载并固定官方构建。"""
    if not path:
        return ensure(bin_dir)
    path = os.path.abspath(os.path.expanduser(path))
    if not os.path.isfile(path):
        raise SystemExit(f"找不到 mihomo 可执行文件：{path}")
    return path


def confirm_proxy_off(yes: bool, ask=input) -> None:
    # 必须在“拉取订阅之前”就关闭透明/系统代理：很多机场会拒绝来自代理/机房 IP 的订阅请求
    # （返回“请关闭网络代理后再获取订阅”），且逐节点测试也需直连以避免二次代理。
    print("\n[2/6] === 现在请手动【关闭透明/系统代理】（如 PassWall、OpenClash、TUN 模式）===")
    print("      原因：订阅服务器通常拒绝经代理 IP 拉取订阅；且测试需直连。")
    if yes:
        print("      已用 --yes 跳过确认，直接继续。")
        return
    ask("      关闭后按回车继续（测试期间不走代理）...")


def main(argv=None) -> int:
    load_env_file(ENV_PATH)
    args = build_parser().parse_args(argv)
    sub_url = resolve_sub_url(args.sub_url)

    os.makedirs(RUN_DIR, exist_ok=True)
    os.makedirs(RESULTS_DIR, exist_ok=True)

    print("[1/6] 准备 mihomo 二进制 ...")
    binary = resolve_binary(args.mihomo, BIN_DIR, ensure_mihomo)

    mixed_port = find_free_port()
    ctrl_port = find_free_port()
    secret = secrets.token_hex(8)
    cfg = build_config(sub_url, mixed_port, ctrl_port, secret, user_agent=args.ua)
    config_path = os.path.join(RUN_DIR, "config.yaml")
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(dump_config(cfg))

    confirm_proxy_off(args.yes)

    print("[3/6] 预检：当前真实出口 IP（应为你的家庭宽带，借此确认代理已关）")
    try:
        d = query_direct(timeout=args.timeout)
        print(f"      直连出口: {d.get('ip')}  {d.get('asOrganization')}  "
              f"fraudScore={d.get('fraudScore')}  residential={d.get('isResidential')}")
    except Exception as e:  # noqa: BLE001
        print(f"      预检直连 IPPure 未通过（不影响逐节点测试，测试走节点出口）：{e}")

    ctrl = MihomoController(binary, RUN_DIR, config_path, ctrl_port, secret)
    try:
        print("\n[4/6] 启动 mihomo 并拉取订阅（代理已关，订阅服务器才会放行）...")
        ctrl.start()
        ctrl.wait_ready()
        members = ctrl.wait_provider()
        if args.limit:
            members = members[: args.limit]
        print(f"      共 {len(members)} 个节点待测。")

        if args.limit:
            ctrl.list_group_members = lambda group="T", _m=members: list(_m)  # type: ignore

        print("\n[5/6] 逐节点检测 ...")

        def progress(i, total, r):
            tag = r.status if r.status != "ok" else f"fraud={r.fraud_score} {r.ip}"
            print(f"      [{i}/{total}] {r.name}: {tag}")

        results = run_checks(ctrl, query_via_proxy, proxy_port=mixed_port,
                             gap=args.gap, timeout=args.timeout, on_progress=progress)
        results = sort_results(results)

        print("\n[6/6] 报表：\n")
        print(render_table(results))
        stamp = _ts()
        csv_path = os.path.join(RESULTS_DIR, f"{args.name}-{stamp}.csv")
        md_path = os.path.join(RESULTS_DIR, f"{args.name}-{stamp}.md")
        write_csv(results, csv_path)
        write_markdown(results, md_path, title=f"{args.name} 节点 IPPure 质检 {stamp}")
        print(f"\n已保存: {csv_path}\n         {md_path}")
        return 0
    finally:
        ctrl.stop()
        print("\n=== 测试结束，请重新【打开透明/系统代理】===")
        if not args.keep_config:
            for fn in ("config.yaml", "mihomo.log", "airport-provider.yaml", "cache.db"):
                try:
                    os.remove(os.path.join(RUN_DIR, fn))
                except OSError:
                    pass


if __name__ == "__main__":
    raise SystemExit(main())
