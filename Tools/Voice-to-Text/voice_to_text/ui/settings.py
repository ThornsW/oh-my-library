"""Settings dialog: recognition services, recognition options, recording, delivery."""

from __future__ import annotations

import copy
import threading
import time

from gi.repository import GLib, Gtk

from .. import __version__
from .. import polish as pl
from ..asr import transcribe
from ..audio import list_input_devices, wav_bytes
from ..config import PROTOCOLS, Config
from ..errors import StageError
from ..log import redact
from ..plugins import PluginSet
from .style import text_of, text_view

AUDIO_FORMATS = {
    "data_uri": "data URI（千问 / DashScope）",
    "base64": "纯 base64 + format（OpenAI 官方）",
}
LANGUAGES = {"auto": "自动检测（中英混说推荐）", "zh": "中文 zh", "en": "英文 en",
             "yue": "粤语 yue", "ja": "日语 ja"}
DEFAULT_DEVICE = "__default__"  # combo ids cannot be empty


def combo(items: dict, current: str) -> Gtk.ComboBoxText:
    c = Gtk.ComboBoxText()
    for key, label in items.items():
        c.append(key, label)
    if not c.set_active_id(current):
        c.set_active(0)
    return c


def editable_combo(options: list[str], current: str) -> Gtk.ComboBoxText:
    c = Gtk.ComboBoxText.new_with_entry()
    for o in options:
        c.append_text(o)
    c.get_child().set_text(current)
    return c


def spin(lo: float, hi: float, step: float, value: float, digits: int = 0) -> Gtk.SpinButton:
    s = Gtk.SpinButton.new_with_range(lo, hi, step)
    s.set_digits(digits)
    s.set_value(value)
    return s


class Form(Gtk.Grid):
    def __init__(self):
        super().__init__(column_spacing=10, row_spacing=8)
        self.set_border_width(12)
        self._row = 0

    def add(self, label: str, widget: Gtk.Widget) -> None:
        if label:
            lab = Gtk.Label(label=label, xalign=1)
            lab.set_line_wrap(True)
            self.attach(lab, 0, self._row, 1, 1)
        widget.set_hexpand(True)
        self.attach(widget, 1, self._row, 1, 1)
        self._row += 1

    def full(self, widget: Gtk.Widget) -> None:
        self.attach(widget, 0, self._row, 2, 1)
        self._row += 1


def scrolled(widget: Gtk.Widget) -> Gtk.ScrolledWindow:
    scroll = Gtk.ScrolledWindow()
    scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scroll.add(widget)
    return scroll


def hint(text: str) -> Gtk.Label:
    lab = Gtk.Label(label=text, xalign=0)
    lab.set_line_wrap(True)
    lab.set_max_width_chars(50)
    lab.get_style_context().add_class("hint")
    return lab


class SettingsDialog(Gtk.Dialog):
    def __init__(self, cfg: Config, parent: Gtk.Window):
        super().__init__(title="设置", transient_for=parent, modal=True)
        self.cfg = cfg
        self.set_default_size(640, 720)
        self.add_button("取消", Gtk.ResponseType.CANCEL)
        self.add_button("保存", Gtk.ResponseType.OK)
        self.providers = copy.deepcopy(cfg["providers"])
        self._current = -1

        tabs = Gtk.Notebook()
        tabs.append_page(self._provider_tab(), Gtk.Label(label="识别服务"))
        tabs.append_page(self._recognition_tab(), Gtk.Label(label="识别"))
        tabs.append_page(self._polish_tab(), Gtk.Label(label="润色"))
        tabs.append_page(self._plugins_tab(), Gtk.Label(label="插件"))
        tabs.append_page(self._recording_tab(), Gtk.Label(label="录音"))
        tabs.append_page(self._delivery_tab(), Gtk.Label(label="投递"))
        self.error = Gtk.Label(xalign=0)
        self.error.set_line_wrap(True)
        self.error.get_style_context().add_class("error-text")
        area = self.get_content_area()
        area.pack_start(tabs, True, True, 0)
        area.pack_start(self.error, False, False, 6)
        area.pack_start(hint(f"Voice-to-Text v{__version__} · MIT License"), False, False, 4)
        self.show_all()

    def run_and_save(self) -> bool:
        """Show the dialog; returns True when settings were saved."""
        while True:
            if self.run() != Gtk.ResponseType.OK:
                self.destroy()
                return False
            if self._save():
                self.destroy()
                return True

    # ---------- tabs ----------

    def _provider_tab(self) -> Gtk.Widget:
        self.provider_combo = Gtk.ComboBoxText()
        for p in self.providers:
            self.provider_combo.append_text(p["name"])
        add_btn, del_btn = Gtk.Button(label="新增"), Gtk.Button(label="删除")
        add_btn.connect("clicked", lambda _b: self._add_provider())
        del_btn.connect("clicked", lambda _b: self._delete_provider())

        self.p_name = Gtk.Entry()
        self.p_protocol = combo(PROTOCOLS, "")
        self.p_url = Gtk.Entry()
        self.p_model = Gtk.Entry()
        self.p_key = Gtk.Entry(visibility=False)
        show_key = Gtk.CheckButton(label="显示")
        show_key.connect("toggled", lambda b: self.p_key.set_visibility(b.get_active()))
        self.p_audio = combo(AUDIO_FORMATS, "data_uri")
        extra_scroll, self.p_extra = text_view("", 80)
        test_btn = Gtk.Button(label="测试连接")
        test_btn.connect("clicked", lambda _b: self._test())
        self.test_result = Gtk.Label(xalign=0)
        self.test_result.set_line_wrap(True)
        self.test_result.set_max_width_chars(50)
        self.test_result.set_selectable(True)

        top = Gtk.Box(spacing=6)
        top.pack_start(Gtk.Label(label="当前使用："), False, False, 0)
        top.pack_start(self.provider_combo, True, True, 0)
        top.pack_start(add_btn, False, False, 0)
        top.pack_start(del_btn, False, False, 0)
        key_row = Gtk.Box(spacing=6)
        key_row.pack_start(self.p_key, True, True, 0)
        key_row.pack_start(show_key, False, False, 0)
        form = Form()
        form.full(top)
        form.add("名称", self.p_name)
        form.add("接口类型", self.p_protocol)
        form.add("接口地址", self.p_url)
        form.add("模型", self.p_model)
        form.add("API Key", key_row)
        form.add("音频编码", self.p_audio)
        form.add("附加参数（JSON）", extra_scroll)
        form.full(test_btn)
        form.full(self.test_result)
        form.full(hint("同一接口类型的模型只需改「模型」。API Key 以明文保存在程序目录的 config.json，"
                       "请勿把该文件提交到代码仓库。"))

        active = self.cfg["active_provider"]
        idx = next((i for i, p in enumerate(self.providers) if p["name"] == active), 0)
        self.provider_combo.connect("changed", lambda c: self._switch_provider(c.get_active()))
        self.provider_combo.set_active(idx)
        self._switch_provider(idx)
        return form

    def _recognition_tab(self) -> Gtk.Widget:
        c = self.cfg
        self.language = combo(LANGUAGES, c["language"] or "auto")
        ctx_scroll, self.context = text_view(c["context"], 80)
        rules_scroll, self.replacements = text_view(c["replacements"], 120)
        self.strip_period = Gtk.CheckButton(label="去掉末尾句号")
        self.strip_period.set_active(bool(c["strip_trailing_period"]))
        self.timeout = spin(5, 120, 1, int(c["request_timeout_s"]))
        form = Form()
        form.add("语言", self.language)
        form.add("热词 / 上下文", ctx_scroll)
        form.add("替换规则", rules_scroll)
        form.full(hint("每行一条：识别错的词 => 正确的词，例如：cloud code => Claude Code"))
        form.add("", self.strip_period)
        form.add("请求超时（秒）", self.timeout)
        return form

    def _polish_tab(self) -> Gtk.Widget:
        c = self.cfg
        self.pl_enabled = Gtk.CheckButton(label="启用润色：识别后再用文字模型整理一遍（每句多等约 1 秒）")
        self.pl_enabled.set_active(bool(c["polish_enabled"]))
        self.pl_reuse = Gtk.CheckButton(label="沿用「识别服务」页当前服务的接口地址和 API Key")
        self.pl_reuse.set_active(bool(c["polish_reuse_provider"]))
        self.pl_url = Gtk.Entry(text=c["polish_base_url"] or "")
        self.pl_model = Gtk.Entry(text=c["polish_model"] or "")
        self.pl_key = Gtk.Entry(visibility=False, text=c["polish_api_key"] or "")
        show_key = Gtk.CheckButton(label="显示")
        show_key.connect("toggled", lambda b: self.pl_key.set_visibility(b.get_active()))
        self.pl_key_row = Gtk.Box(spacing=6)
        self.pl_key_row.pack_start(self.pl_key, True, True, 0)
        self.pl_key_row.pack_start(show_key, False, False, 0)
        self.pl_reuse.connect("toggled", lambda _b: self._sync_polish_reuse())
        self._sync_polish_reuse()
        prompt_scroll, self.pl_prompt = text_view(c["polish_prompt"] or pl.DEFAULT_PROMPT, 170)
        reset = Gtk.Button(label="恢复默认提示词")
        reset.connect("clicked", lambda _b: self.pl_prompt.get_buffer().set_text(pl.DEFAULT_PROMPT))
        extra_scroll, self.pl_extra = text_view(c["polish_extra_json"] or "", 50)
        self.pl_timeout = spin(3, 60, 1, int(c["polish_timeout_s"]))
        test_btn = Gtk.Button(label="测试润色")
        test_btn.connect("clicked", lambda _b: self._test_polish())
        self.pl_result = Gtk.Label(xalign=0)
        self.pl_result.set_line_wrap(True)
        self.pl_result.set_max_width_chars(50)
        self.pl_result.set_selectable(True)
        form = Form()
        form.full(self.pl_enabled)
        form.full(self.pl_reuse)
        form.add("接口地址", self.pl_url)
        form.add("API Key", self.pl_key_row)
        form.add("模型", self.pl_model)
        form.add("提示词", prompt_scroll)
        form.add("", reset)
        form.add("附加参数（JSON）", extra_scroll)
        form.add("超时（秒）", self.pl_timeout)
        form.full(test_btn)
        form.full(self.pl_result)
        form.full(hint("需要 OpenAI 兼容的聊天接口（{地址}/chat/completions）。"
                       "润色失败或超时会照常发送原话。「热词」会一起发给模型。"
                       "默认附加参数用来关闭千问的思考模式；换用别家服务报 HTTP 400 时，把它清空。"))
        return scrolled(form)

    def _sync_polish_reuse(self) -> None:
        own = not self.pl_reuse.get_active()
        self.pl_url.set_sensitive(own)
        self.pl_key_row.set_sensitive(own)

    def _polish_settings(self) -> dict:
        prompt = text_of(self.pl_prompt).strip()
        return {
            "polish_reuse_provider": self.pl_reuse.get_active(),
            "polish_base_url": self.pl_url.get_text().strip(),
            "polish_api_key": self.pl_key.get_text().strip(),
            "polish_model": self.pl_model.get_text().strip(),
            # store "" for the built-in prompt so later improvements to it apply
            "polish_prompt": "" if prompt == pl.DEFAULT_PROMPT.strip() else prompt,
            "polish_extra_json": text_of(self.pl_extra).strip(),
        }

    def _test_polish(self) -> None:
        self._store_form()
        provider = dict(self.providers[self._current]) if self.providers else None
        sample = "嗯那个就是帮我帮我看一下这个这个 bug 是怎么回事"
        context, timeout = text_of(self.context).strip(), self.pl_timeout.get_value_as_int()
        try:
            service = pl.resolve_service(self._polish_settings(), provider)
        except StageError as e:
            self.pl_result.set_text(f"✗ {e}")
            return
        self.pl_result.set_text("测试中…")

        def job():
            t0 = time.monotonic()
            try:
                out = pl.polish(service, sample, context, timeout)
                msg = f"✓ {(time.monotonic() - t0) * 1000:.0f} ms\n原话：{sample}\n润色：{out}"
            except StageError as e:
                msg = redact(f"✗ {e}\n{e.detail}".strip())
            GLib.idle_add(lambda: self.pl_result.set_text(msg) or False)

        threading.Thread(target=job, daemon=True).start()

    def _plugins_tab(self) -> Gtk.Widget:
        self.plugin_set = PluginSet(self.cfg.plugins_dir)
        self._enabled_plugins = set(self.cfg["plugins_enabled"] or [])
        self.plugin_checks: dict[str, Gtk.CheckButton] = {}
        self.plugin_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        open_btn = Gtk.Button(label="打开插件文件夹")
        open_btn.connect("clicked", lambda _b: self._open_plugins_dir())
        refresh = Gtk.Button(label="刷新列表")
        refresh.connect("clicked", lambda _b: self._fill_plugins())
        buttons = Gtk.Box(spacing=6)
        buttons.pack_start(open_btn, False, False, 0)
        buttons.pack_start(refresh, False, False, 0)
        self.plugin_sample = Gtk.Entry(text="嗯，对。你看一下「设置」页面（第二个）里的选项？")
        self.plugin_sample.connect("changed", lambda _e: self._test_plugins())
        self.plugin_result = Gtk.Label(xalign=0)
        self.plugin_result.set_line_wrap(True)
        self.plugin_result.set_selectable(True)
        form = Form()
        form.full(hint("插件是程序目录 plugins/ 里的 .rules 文件，每行一条「正则 => 替换」。"
                       "勾选的插件按文件名顺序，在润色之后对每句识别结果做最后一步处理。"
                       "改了文件不用重启，下一句就生效；新加的文件点「刷新列表」。"))
        form.full(self.plugin_box)
        form.full(buttons)
        form.add("测试句", self.plugin_sample)
        form.add("结果", self.plugin_result)
        self._fill_plugins()
        return scrolled(form)

    def _fill_plugins(self) -> None:
        for name, check in self.plugin_checks.items():  # keep unsaved ticks across a refresh
            (self._enabled_plugins.add if check.get_active() else self._enabled_plugins.discard)(name)
        for child in self.plugin_box.get_children():
            child.destroy()
        self.plugin_checks = {}
        plugins = self.plugin_set.all()
        if not plugins:
            self.plugin_box.pack_start(hint(f"{self.cfg.plugins_dir} 里还没有 .rules 文件"), False, False, 0)
        for p in plugins:
            check = Gtk.CheckButton(label=f"{p.name}（{len(p.rules)} 条规则）")
            check.set_active(p.name in self._enabled_plugins)
            check.connect("toggled", lambda _c: self._test_plugins())
            self.plugin_box.pack_start(check, False, False, 0)
            self.plugin_checks[p.name] = check
            if p.errors:
                more = f" 等 {len(p.errors)} 处" if len(p.errors) > 3 else ""
                err = Gtk.Label(label="⚠ 跳过了写错的规则：" + "；".join(p.errors[:3]) + more, xalign=0)
                err.set_line_wrap(True)
                err.set_max_width_chars(50)
                err.get_style_context().add_class("error-text")
                self.plugin_box.pack_start(err, False, False, 0)
        self.plugin_box.show_all()
        self._test_plugins()

    def _checked_plugins(self) -> list[str]:
        return [name for name, check in self.plugin_checks.items() if check.get_active()]

    def _test_plugins(self) -> None:
        self.plugin_result.set_text(self.plugin_set.apply(self.plugin_sample.get_text(), self._checked_plugins()))

    def _open_plugins_dir(self) -> None:
        self.plugin_set.ensure_builtin()
        d = self.cfg.plugins_dir
        try:
            d.mkdir(parents=True, exist_ok=True)
            Gtk.show_uri_on_window(self, d.as_uri(), Gtk.get_current_event_time())
        except (OSError, GLib.Error) as e:
            self.error.set_text(f"打不开插件文件夹 {d}：{getattr(e, 'message', e)}")

    def _recording_tab(self) -> Gtk.Widget:
        c = self.cfg
        self.device = Gtk.ComboBoxText()
        refresh = Gtk.Button(label="刷新")
        refresh.connect("clicked", lambda _b: self._load_devices(self.device.get_active_id()))
        self._load_devices(c["audio_device"] or DEFAULT_DEVICE)
        self.max_s = spin(5, 280, 5, int(c["max_seconds"]))
        self.min_s = spin(0.1, 3.0, 0.1, float(c["min_seconds"]), 1)
        self.tail = spin(0, 3000, 100, int(c["tail_ms"]))
        self.silence = spin(-90, -10, 1, float(c["silence_threshold_db"]))
        row = Gtk.Box(spacing=6)
        row.pack_start(self.device, True, True, 0)
        row.pack_start(refresh, False, False, 0)
        form = Form()
        form.add("录音设备", row)
        form.add("最长录音（秒）", self.max_s)
        form.add("最短录音（秒）", self.min_s)
        form.add("松手后继续录音（毫秒）", self.tail)
        form.add("静音判定（dB）", self.silence)
        form.full(hint("整段录音最大音量低于「静音判定」时，视为没录到声音，不发给识别服务。"))
        return form

    def _delivery_tab(self) -> Gtk.Widget:
        c = self.cfg
        self.target_mode = combo({"fixed": "固定窗口（点「绑定窗口」指定）",
                                  "follow": "跟随最后使用的窗口"}, c["target_mode"])
        self.paste_keys = editable_combo(["ctrl+shift+v", "ctrl+v", "shift+Insert"], c["paste_keys"])
        self.enter_keys = editable_combo(["Return", "ctrl+Return", "KP_Enter"], c["enter_keys"])
        self.d_paste = spin(0, 3000, 10, int(c["delay_before_paste_ms"]))
        self.d_enter = spin(0, 5000, 50, int(c["delay_before_enter_ms"]))
        form = Form()
        form.add("目标窗口", self.target_mode)
        form.add("粘贴快捷键", self.paste_keys)
        form.add("回车键", self.enter_keys)
        form.add("切换窗口后、粘贴前等待（毫秒）", self.d_paste)
        form.add("粘贴后、回车前等待（毫秒）", self.d_enter)
        form.full(hint("按键写法同 xdotool，例如 ctrl+shift+v。GNOME 终端和 VS Code 终端粘贴都是 ctrl+shift+v。"))
        return form

    # ---------- providers ----------

    def _store_form(self) -> None:
        if 0 <= self._current < len(self.providers):
            p = self.providers[self._current]
            p.update(name=self.p_name.get_text().strip(), protocol=self.p_protocol.get_active_id(),
                     base_url=self.p_url.get_text().strip(), model=self.p_model.get_text().strip(),
                     api_key=self.p_key.get_text().strip(), audio_format=self.p_audio.get_active_id(),
                     extra_json=text_of(self.p_extra).strip())

    def _switch_provider(self, idx: int) -> None:
        if idx == self._current or idx < 0:
            return
        self._store_form()
        old = self._current
        self._current = idx
        if 0 <= old < len(self.providers) and old != idx:
            # keep the old entry's label in sync with an edited name
            name = self.providers[old]["name"] or "（未命名）"
            self._current = -1
            self.provider_combo.remove(old)
            self.provider_combo.insert_text(old, name)
            self.provider_combo.set_active(idx)
            self._current = idx
        p = self.providers[idx]
        self.p_name.set_text(p.get("name", ""))
        self.p_protocol.set_active_id(p.get("protocol", "openai_chat_audio"))
        self.p_url.set_text(p.get("base_url", ""))
        self.p_model.set_text(p.get("model", ""))
        self.p_key.set_text(p.get("api_key", ""))
        self.p_audio.set_active_id(p.get("audio_format", "data_uri"))
        self.p_extra.get_buffer().set_text(p.get("extra_json", ""))
        self.test_result.set_text("")

    def _add_provider(self) -> None:
        self._store_form()
        base = dict(self.providers[self._current]) if self.providers else {}
        base.update(name=f"新服务 {len(self.providers) + 1}", api_key="")
        self.providers.append(base)
        self.provider_combo.append_text(base["name"])
        self.provider_combo.set_active(len(self.providers) - 1)

    def _delete_provider(self) -> None:
        if len(self.providers) <= 1:
            self.error.set_text("至少保留一个识别服务")
            return
        idx = self._current
        self._current = -1
        del self.providers[idx]
        self.provider_combo.remove(idx)
        self.provider_combo.set_active(min(idx, len(self.providers) - 1))

    def _test(self) -> None:
        self._store_form()
        provider = dict(self.providers[self._current])
        self.test_result.set_text("测试中…")
        # One second of faint noise: checks address, key and protocol, not accuracy.
        wav = wav_bytes(bytes((i * 7) % 5 for i in range(32000)))

        def job():
            try:
                text = transcribe(provider, wav, "", "", timeout=20, allow_empty=True)
                msg = f"✓ 连接成功（地址、Key、接口类型都对）。返回：{text or '（空，正常）'}"
            except StageError as e:
                msg = redact(f"✗ {e}\n{e.detail}".strip())
            GLib.idle_add(lambda: self.test_result.set_text(msg) or False)

        threading.Thread(target=job, daemon=True).start()

    # ---------- misc ----------

    def _load_devices(self, current: str | None) -> None:
        self.device.remove_all()
        self.device.append(DEFAULT_DEVICE, "系统默认")
        try:
            for name, desc in list_input_devices():
                self.device.append(name, desc)
        except StageError as e:
            self.error.set_text(str(e))
        if not self.device.set_active_id(current or DEFAULT_DEVICE):
            self.device.set_active(0)

    def _save(self) -> bool:
        self._store_form()
        names = [p["name"] for p in self.providers]
        if any(not n for n in names) or len(set(names)) != len(names):
            self.error.set_text("识别服务的名称不能为空，也不能重复")
            return False
        c = self.cfg
        c["providers"] = self.providers
        c["active_provider"] = self.providers[self._current]["name"]
        lang = self.language.get_active_id()
        c["language"] = "" if lang == "auto" else lang
        c["context"] = text_of(self.context).strip()
        c["replacements"] = text_of(self.replacements)
        c["strip_trailing_period"] = self.strip_period.get_active()
        c["request_timeout_s"] = self.timeout.get_value_as_int()
        c["polish_enabled"] = self.pl_enabled.get_active()
        for k, v in self._polish_settings().items():
            c[k] = v
        c["polish_timeout_s"] = self.pl_timeout.get_value_as_int()
        c["plugins_enabled"] = self._checked_plugins()
        dev = self.device.get_active_id()
        c["audio_device"] = "" if dev in (None, DEFAULT_DEVICE) else dev
        c["max_seconds"] = self.max_s.get_value_as_int()
        c["min_seconds"] = round(self.min_s.get_value(), 2)
        c["tail_ms"] = self.tail.get_value_as_int()
        c["silence_threshold_db"] = self.silence.get_value()
        c["target_mode"] = self.target_mode.get_active_id()
        c["paste_keys"] = self.paste_keys.get_child().get_text().strip() or "ctrl+shift+v"
        c["enter_keys"] = self.enter_keys.get_child().get_text().strip() or "Return"
        c["delay_before_paste_ms"] = self.d_paste.get_value_as_int()
        c["delay_before_enter_ms"] = self.d_enter.get_value_as_int()
        c.save()
        return True
