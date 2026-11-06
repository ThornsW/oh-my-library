"""Text plugins: rule files in plugins/ next to config.json, each line
`regex => replacement`, applied to every recognized sentence as the last step.

Which plugins are on is stored in config.json ("plugins_enabled"), so a rule
file can be shared without also sharing anyone's settings.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .log import log

SUFFIX = ".rules"

BUILTIN = {
    "标点半角": """# 标点统一为英文半角（符号后不加空格）
#
# 写法：每行一条「正则 => 替换」，从上到下依次执行；# 开头的行是注释。
# 替换留空表示删除。替换两端要保留空格时，用英文双引号括起来，例如：， => ", "
# 替换里可以用 \\g<1> 引用正则里的第 1 个括号。
，|、 => ,
。 => .
？ => ?
！ => !
： => :
； => ;
（ => (
） => )
【 => [
】 => ]
《 => <
》 => >
[“”「」『』] => "
[‘’] => '
…+ => ...
—+ => -
～ => ~
％ => %
""",
}


@dataclass
class Rule:
    line: int
    pattern: re.Pattern
    repl: str


@dataclass
class Plugin:
    name: str
    path: Path
    rules: list[Rule] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)  # "第 3 行：…", shown in settings


def parse(text: str) -> tuple[list[Rule], list[str]]:
    rules, errors = [], []
    for no, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=>" not in line:
            errors.append(f"第 {no} 行：缺少 =>")
            continue
        pattern, repl = (s.strip() for s in line.split("=>", 1))
        if len(repl) >= 2 and repl[0] == repl[-1] == '"':
            repl = repl[1:-1]
        if not pattern:
            errors.append(f"第 {no} 行：=> 左边的正则是空的")
            continue
        try:
            compiled = re.compile(pattern)
            compiled.sub(repl, "")  # checks the replacement too (bad escapes, group numbers)
        except (re.error, IndexError) as e:
            errors.append(f"第 {no} 行：{e}")
            continue
        rules.append(Rule(no, compiled, repl))
    return rules, errors


def apply(text: str, plugins: list[Plugin]) -> str:
    for p in plugins:
        for r in p.rules:
            text = r.pattern.sub(r.repl, text)
    # A newline would act like Enter in the terminal.
    return re.sub(r"\s*[\r\n]+\s*", " ", text).strip()


class PluginSet:
    """Reads plugins/ on demand; a file is parsed again only after it changes,
    so edits take effect on the next sentence without restarting."""

    def __init__(self, directory: Path):
        self.dir = directory
        self._cache: dict[Path, tuple[float, Plugin]] = {}

    def ensure_builtin(self) -> None:
        """First run only: create the folder with the built-in plugins. After that
        the files belong to the user (edited or deleted ones are not restored)."""
        if self.dir.exists():
            return
        try:
            self.dir.mkdir(parents=True)
            for name, body in BUILTIN.items():
                (self.dir / f"{name}{SUFFIX}").write_text(body, encoding="utf-8")
        except OSError as e:
            log.warning("plugins: cannot create %s: %s", self.dir, e)

    def _load(self, path: Path) -> Plugin | None:
        try:
            mtime = path.stat().st_mtime
            cached = self._cache.get(path)
            if cached and cached[0] == mtime:
                return cached[1]
            rules, errors = parse(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError) as e:
            log.warning("plugins: cannot read %s: %s", path.name, e)
            return Plugin(path.stem, path, errors=[f"读不了这个文件：{e}"])
        plugin = Plugin(path.stem, path, rules, errors)
        for err in errors:
            log.warning("plugins: %s %s", path.name, err)
        self._cache[path] = (mtime, plugin)
        return plugin

    def all(self) -> list[Plugin]:
        """Every plugin file, in file-name order (put numbers in front to reorder)."""
        if not self.dir.is_dir():
            return []
        return [p for path in sorted(self.dir.glob(f"*{SUFFIX}")) if (p := self._load(path))]

    def apply(self, text: str, enabled: list[str]) -> str:
        on = set(enabled or [])
        active = [p for p in self.all() if p.name in on]
        return apply(text, active) if active else text
