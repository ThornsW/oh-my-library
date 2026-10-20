# IP-check2ippure maintenance guide

This document holds details needed for code and workflow changes. Ordinary edits should
start from `AGENTS.md` and load this guide only when its subject applies.

## Architecture

`check_airport.py` owns CLI parsing and the interactive runtime sequence. Business logic
is split across small modules:

| Path | Responsibility |
|---|---|
| `core/binary.py` | Select, download, extract, and pin the mihomo binary by SHA-256 |
| `core/config_gen.py` | Build the loopback-only mihomo configuration as JSON-compatible YAML |
| `core/mihomo.py` | Start and stop mihomo and call its authenticated controller API |
| `core/ippure.py` | Query IPPure directly or through the selected proxy |
| `core/runner.py` | Switch nodes serially and collect results without aborting the batch |
| `core/classify.py` | Map IPPure responses and classify likely datacenter addresses |
| `core/report.py` | Sort and render terminal, CSV, and Markdown reports |
| `core/netutil.py` | Allocate local ports and provide controller HTTP helpers |
| `core/envfile.py` | Read `KEY=VALUE` lines from the program-local `.env` without overriding existing variables |

Keep orchestration in `check_airport.py`; keep reusable logic in `core/`. Tests mirror
these boundaries and use `unittest` plus local fake HTTP services.

## Runtime sequence

1. Resolve the subscription URL: CLI argument, then `IPPURE_SUB_URL` (the program-local
   `.env` only fills missing variables), then a no-echo prompt.
2. Use `--mihomo` / `MIHOMO_BIN` when given; otherwise reuse a SHA-pinned `bin/mihomo`, or
   download the current official build on first use.
3. Write an authenticated controller configuration under `run/` using free loopback
   ports. `--ua` sets the subscription request User-Agent.
4. Ask the user to disable the active transparent/system proxy before fetching the
   subscription. Some providers reject requests from proxy or datacenter addresses.
   `--yes` skips the Enter prompt but still prints the reminder.
5. Start mihomo with its home directory fixed to `run/`, obtain provider members, and
   switch through them serially.
6. Query IPPure through each selected node, preserving timeout and rate-limit failures as
   row statuses so one bad node does not end the batch.
7. Write sorted CSV and Markdown output under `results/`, stop mihomo in `finally`, clean
   transient files unless `--keep-config` is set, and remind the user to restore the
   system proxy.

The direct IPPure preflight is informational. It helps the user recognize that the
system proxy is still enabled but must not silently change host or router settings.

## Containment and sensitive data

- `bin/`, `run/`, and generated `results/*` are ignored. Keep that boundary intact.
- A subscription URL commonly embeds an access token. Use placeholders in tests,
  examples, commits, issue text, and documentation.
- Reports expose node names, exit IPs, ASN data, and location data. Do not promote them
  into tracked fixtures.
- The controller listens on `127.0.0.1`, uses a random secret, and is stopped on normal
  exit, exceptions, and interruption.
- The generated configuration intentionally omits GEOIP and GEOSITE rules so mihomo does
  not populate user-level data directories.

## Validation boundaries

The full local suite is offline and safe to rerun after implementation changes:

```bash
<absolute-project-python> -m unittest discover -s tests -t . -v
```

The project uses the Miniforge `GeneralDev` environment (Python 3.12); any Python 3.10+
interpreter works because the code is standard-library only. Do not fall back to `base`. Use focused modules during iteration, then run the full suite
before finishing. `--help` is also local, but it adds little once argument parsing is
covered.

A real `check_airport.py` run is not a smoke test. It can download a binary, fetch a live
subscription, start local listeners, contact every selected node and IPPure, and write a
sensitive report. Run it only when the task calls for live validation and the user has
provided the required subscription and can perform the manual proxy transition.

## Historical records

- `docs/2026-06-02-ip-check2ippure-design.md` records the accepted initial design.
- `docs/2026-06-02-ip-check2ippure.md` is the completed construction plan and contains
  copied implementation snippets, obsolete paths, and old execution instructions.

These files remain locally ignored because they include machine-specific and private
operational details. Prefer the current code, tests, README, and this guide when they
disagree.
