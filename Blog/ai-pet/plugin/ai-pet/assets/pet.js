/* AI 宠物：左下角的看板角色 + 聊天气泡。原生 JS，无依赖。
 * 角色二选一：JS 角色文件（window.AIPET_CHARACTER，逐帧画进 canvas），或后台上传的图片（每种表情一张）。
 * 主题用无刷新换页（如 Argon 的 PJAX）时只替换正文区域，挂在 body 末尾的 #aipet 会一直保留；
 * 靠轮询 location.href 发现换页。 */
(function () {
	'use strict';
	if (window.__aipetLoaded) return;
	window.__aipetLoaded = true;
	const CFG = window.AIPET || {};
	const CHAR = window.AIPET_CHARACTER;
	const IMGS = CFG.images || {};
	if (!(CHAR && typeof CHAR.draw === 'function') && !IMGS.normal) return;
	const NAME = CFG.name || '小助手';

	// ================= 角色渲染 =================
	// 两种渲染器接口相同：el 是显示用的元素；up / down 是探头、趴着时的上下偏移；
	// draw(s, key) 画一帧；fxTop(s) 是表情符号离顶部的距离（px）。
	// s = { expr, blink, talk, look, ear, rise }，含义见 README「JS 角色文件」
	function canvasRenderer(ch) {
		const el = document.createElement('canvas');
		el.width = ch.width;
		el.height = ch.height;
		const ctx = el.getContext('2d'), cache = new Map();
		return {
			el, pixel: ch.pixelated !== false,
			up: ch.rise ? ch.rise.up : 0, down: ch.rise ? ch.rise.down : 0,
			draw(s, key) {
				let c = cache.get(key);
				if (!c) {
					if (cache.size > 500) cache.clear();
					c = document.createElement('canvas');
					c.width = ch.width;
					c.height = ch.height;
					ch.draw(c.getContext('2d'), s);
					cache.set(key, c);
				}
				ctx.clearRect(0, 0, ch.width, ch.height);
				ctx.drawImage(c, 0, 0);
			},
			fxTop: s => (s.rise + 2) * el.clientWidth / ch.width,
		};
	}
	// 图片角色：按表情换图；说话时在「说话」图和表情图之间来回切，普通表情眨眼时换「眨眼」图；探头靠上下位移
	function imageRenderer(imgs) {
		const el = document.createElement('img');
		el.alt = '';
		el.draggable = false;
		Object.values(imgs).forEach(u => { new Image().src = u; });
		return {
			el, pixel: !!CFG.pixel, up: 0, down: 4,
			draw(s) {
				const src = (s.talk && imgs.talk) || (s.blink && s.expr === 'normal' && imgs.blink) || imgs[s.expr] || imgs.normal;
				if (el.getAttribute('src') !== src) el.src = src;
				el.style.transform = 'translateY(' + s.rise * 2 + '%)';
			},
			fxTop: s => s.rise * .02 * el.clientHeight,
		};
	}
	const R = CHAR && typeof CHAR.draw === 'function' ? canvasRenderer(CHAR) : imageRenderer(IMGS);
	const UP = R.up, DOWN = R.down;

	// ================= 台词 =================
	const EXPRS = ['normal', 'happy', 'shy', 'surprised', 'sleepy'];
	const FX = { happy: '✦', shy: '💦', surprised: '!', sleepy: 'z Z' };
	// 默认台词，[文字, 表情]。{name} 角色名，{site} 站名，{t} 文章标题。JS 角色文件里的 lines / fail 会覆盖同名的项
	const TIPS = Object.assign({
		home:  [['欢迎来到「{site}」～点我可以聊天哦！', 'happy'], ['首页文章好多，要不要我帮你挑一篇？', 'normal']],
		post:  [['在看《{t}》呀，有看不懂的可以问我～', 'normal'], ['《{t}》……{name}也看过哦！', 'happy']],
		anime: [['这是站长的看番清单！想让我推荐一部吗？', 'happy'], ['这么多番，是不是挑花眼了？', 'normal']],
		other: [['找到想看的了吗？可以问问{name}。', 'normal']],
		night: [['都这么晚了……你还不睡吗？', 'sleepy'], ['夜猫子你好～{name}也还醒着。', 'sleepy']],
		dark:  [['关灯啦，夜间模式开启！', 'surprised']],
		light: [['开灯了，好亮！', 'surprised']],
		poke:  [['哎呀！', 'surprised'], ['别、别戳啦……', 'shy'], ['要摸摸头吗？轻一点～', 'happy'], ['（盯——）', 'normal']],
		idle:  [['（盯——）', 'normal'], ['今天也要开开心心的。', 'happy'], ['无聊的话可以点我聊天哦。', 'normal']],
		back:  [['你叫我呀？{name}回来啦！', 'happy']],
		chat:  [['想聊什么？问我站里的文章都行～', 'happy']],
	}, CHAR && CHAR.lines);
	const FAIL = Object.assign({
		limit: ['今天聊得太多啦，{name}要去休息了……明天再来找我吧！', 'sleepy'],
		off: ['{name}现在只会打招呼……（聊天功能没开）', 'shy'],
		bad: ['说得太长啦，200 个字以内好不好～', 'surprised'],
		forbidden: ['咦？你是从哪里来的……', 'surprised'],
		error: ['刚刚走神了，没听清，再说一次？', 'surprised'],
	}, CHAR && CHAR.fail);
	const TAGS = { 开心: 'happy', 害羞: 'shy', 惊讶: 'surprised', 困了: 'sleepy', 普通: 'normal' };

	const pick = a => a[Math.floor(Math.random() * a.length)];
	const fill = t => String(t).replace(/\{name\}/g, NAME).replace(/\{site\}/g, CFG.site || '');
	const pickLine = list => { const [t, e] = pick(list); return [fill(t), e]; };
	const failLine = code => { const [t, e] = FAIL[code] || FAIL.error; return [fill(t), e]; };
	const hour = () => new Date().getHours();
	const isNight = () => hour() >= 23 || hour() < 5;
	const restExpr = () => isNight() ? 'sleepy' : 'normal';
	const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
	const safe = fn => { try { return fn(); } catch (e) { return null; } };
	const trimSlash = u => String(u || '').split('#')[0].replace(/\/+$/, '');

	// 主题的夜间模式：常见做法是给 <html> / <body> 加类名或 data 属性（Argon 用 html.darkmode）
	const DARK_CLASSES = ['darkmode', 'dark', 'dark-mode', 'theme-dark', 'night', 'night-mode'];
	const DARK_ATTRS = ['data-theme', 'data-bs-theme', 'data-color-scheme', 'data-color-mode', 'data-mode'];
	const sysDark = matchMedia('(prefers-color-scheme: dark)');
	function isDark() {
		if (CFG.dark === 'off') return false;
		if (CFG.dark === 'system') return sysDark.matches;
		return [document.documentElement, document.body].some(el => el && (
			DARK_CLASSES.some(c => el.classList.contains(c)) ||
			DARK_ATTRS.some(a => (el.getAttribute(a) || '').toLowerCase() === 'dark')));
	}

	// ================= 组件 =================
	let root, cat, bubble, form, input, fx;
	const S = { expr: 'normal', blink: false, breath: 0, rise: DOWN, look: 0, ear: 0, talking: false, talkOpen: false,
		hover: false, bubble: false, chat: false, busy: false, hidden: false };
	let tick = 0, timer = 0, nextBlink = 30, lastKey = '', lastHref = location.href, idleAt = 0;
	let mouseX = null, mouseT = 0, rect = null;

	function draw() {
		const s = { expr: S.expr, blink: S.blink, talk: S.talking && S.talkOpen, look: S.look, ear: S.ear, rise: S.rise + S.breath };
		const key = [s.expr, s.blink, s.talk, s.look, s.ear, s.rise].join('|');
		if (key === lastKey) return;
		lastKey = key;
		R.draw(s, key);
		fx.style.top = R.fxTop(s) + 'px';
	}

	function setExpr(name) {
		S.expr = EXPRS.includes(name) ? name : 'normal';
		const f = FX[S.expr];
		fx.textContent = f || '';
		fx.className = 'aipet-fx' + (f ? ' is-on aipet-fx-' + S.expr : '');
		lastKey = '';
		draw();
	}

	function lookDir() {
		if (mouseX === null || performance.now() - mouseT > 5000) return 0;
		const r = rect || (rect = cat.getBoundingClientRect());
		const dx = mouseX - (r.left + r.width / 2);
		return Math.abs(dx) < r.width * .4 ? 0 : Math.sign(dx);
	}

	function loop() {
		tick++;
		if (reduce) S.rise = S.hidden ? DOWN : UP;
		else {
			const target = !S.hidden && (S.hover || S.bubble || S.chat) ? UP : DOWN, d = target - S.rise;
			S.rise += Math.sign(d) * Math.min(2, Math.abs(d));
			S.breath = Math.floor(tick / 7) % 2;
			if (tick >= nextBlink) { S.blink = true; nextBlink = tick + 25 + Math.random() * 40; } else S.blink = false;
			S.ear = S.ear > 0 ? S.ear - 1 : Math.random() < .008 ? 3 : 0;
			S.look = lookDir();
			if (S.talking) S.talkOpen = Math.random() < .6;
		}
		if (location.href !== lastHref) {
			lastHref = location.href;
			setTimeout(() => greet(false), 1200);
		}
		if (!S.hidden && !S.bubble && !S.chat && Date.now() > idleAt) {
			idleAt = Date.now() + 75000 + Math.random() * 75000;
			if (tick > 50 && Math.random() < .5) say(...pickLine(TIPS.idle));
		}
		draw();
	}
	function run(on) {
		clearInterval(timer);
		timer = on ? setInterval(loop, 100) : 0;
	}

	// ---------- 气泡 ----------
	let typeTimer = 0, hideTimer = 0;
	// 把回答切成文字段和链接段；只有本站链接变成 <a>，站外链接只留文字
	function segments(text) {
		const re = /\[([^\]\n]{1,80})\]\((https?:\/\/[^\s)]+)\)|(https?:\/\/[^\s<>"'（）()【】「」《》，。！？、；：]+)/g;
		const out = [];
		let last = 0, m;
		while ((m = re.exec(text))) {
			if (m.index > last) out.push({ t: text.slice(last, m.index) });
			const href = m[2] || m[3];
			const own = safe(() => new URL(href, location.href).host === location.host);
			const label = m[1] || (own ? safe(() => decodeURIComponent(new URL(href).pathname)) || href : href);
			out.push(own ? { t: label, href } : { t: label });
			last = m.index + m[0].length;
		}
		if (last < text.length) out.push({ t: text.slice(last) });
		return out;
	}
	function renderUpTo(segs, n) {
		const frag = document.createDocumentFragment();
		for (const s of segs) {
			if (n <= 0) break;
			const part = Array.from(s.t).slice(0, n).join('');
			n -= Array.from(s.t).length;
			if (s.href) {
				const a = document.createElement('a');
				a.href = s.href;
				a.textContent = part;
				frag.append(a);
			} else frag.append(part);
		}
		bubble.replaceChildren(frag);
	}
	function showBubble(on) {
		S.bubble = on;
		bubble.classList.toggle('is-on', on);
	}
	function say(text, expr = 'normal', keep = false) {
		if (S.hidden) return;
		clearInterval(typeTimer);
		clearTimeout(hideTimer);
		bubble.classList.remove('is-thinking');
		setExpr(expr);
		const segs = segments(text), total = segs.reduce((n, s) => n + Array.from(s.t).length, 0);
		showBubble(true);
		const done = () => {
			clearInterval(typeTimer);
			S.talking = false;
			renderUpTo(segs, total);
			if (!keep) hideTimer = setTimeout(() => {
				if (!S.chat) showBubble(false);
				setExpr(restExpr());
			}, Math.max(4500, total * 160));
		};
		if (reduce) return done();
		let i = 0;
		S.talking = true;
		typeTimer = setInterval(() => {
			i++;
			renderUpTo(segs, i);
			if (i >= total) done();
		}, 45);
	}

	// 当前是文章或页面详情时返回标题，否则返回空字符串
	function postTitle() {
		// Argon：列表页也用文章卡片，只有详情页的 article 带 post-full；PJAX 换页后 body 的类名不会更新，所以只看这个
		if (window.argonConfig) {
			const h = document.querySelector('#primary article.post-full .post-title');
			return h ? h.textContent.trim() : '';
		}
		// 其他主题：WordPress 给详情页的 body 加 single / page 类名
		const b = document.body.classList;
		if (!(b.contains('single') || (b.contains('page') && !b.contains('home')))) return '';
		const h = document.querySelector('h1.entry-title, h1.wp-block-post-title, .wp-block-post-title, h1.post-title, article h1, main h1');
		return h ? h.textContent.trim() : '';
	}

	function greet(first) {
		if (S.hidden || S.chat || S.busy) return;
		const here = trimSlash(location.href);
		let kind = 'other', title = '';
		if (CFG.anime && here === trimSlash(CFG.anime)) kind = 'anime';
		else if (here === trimSlash(CFG.home)) kind = 'home';
		else {
			title = postTitle();
			if (title.length > 22) title = title.slice(0, 21) + '…';
			if (title) kind = 'post';
		}
		if (first && isNight()) kind = 'night';
		const [text, expr] = pickLine(TIPS[kind]);
		say(text.replace('{t}', title), expr);
	}

	// ---------- 聊天 ----------
	const HKEY = 'aipet-history';
	const loadHist = () => safe(() => JSON.parse(sessionStorage.getItem(HKEY))) || [];
	function saveHist(q, a) {
		const h = loadHist().concat([{ role: 'user', content: q }, { role: 'assistant', content: a }]).slice(-12);
		safe(() => sessionStorage.setItem(HKEY, JSON.stringify(h)));
	}
	function setChat(on) {
		S.chat = on;
		root.classList.toggle('is-chat', on);
		if (on) {
			if (!S.bubble) { const [text, expr] = pickLine(TIPS.chat); say(text, expr, true); }
			input.focus({ preventScroll: true });
		} else {
			hideTimer = setTimeout(() => showBubble(false), 1500);
		}
	}
	// 一个标签页一段对话：后台聊天记录按它分组
	function sessionId() {
		let id = safe(() => sessionStorage.getItem('aipet-sid'));
		if (!id) {
			id = self.crypto && crypto.randomUUID ? crypto.randomUUID() : Date.now().toString(36) + Math.random().toString(36).slice(2, 12);
			safe(() => sessionStorage.setItem('aipet-sid', id));
		}
		return id;
	}
	async function send(text) {
		if (S.busy || !text) return;
		S.busy = true;
		input.value = '';
		input.disabled = true;
		clearInterval(typeTimer);
		clearTimeout(hideTimer);
		S.talking = false;
		setExpr('normal');
		bubble.textContent = '思考中';
		bubble.classList.add('is-thinking');
		showBubble(true);
		let reply, expr;
		try {
			const ctrl = new AbortController(), stop = setTimeout(() => ctrl.abort(), 30000);
			const r = await fetch(CFG.rest, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ message: text, history: loadHist(), url: location.href, sid: sessionId() }),
				credentials: 'same-origin',
				signal: ctrl.signal,
			});
			clearTimeout(stop);
			const d = await r.json().catch(() => ({}));
			if (r.ok && d.reply) {
				const m = d.reply.match(/^\s*[[【](开心|害羞|惊讶|困了|普通)[\]】]\s*/);
				reply = (m ? d.reply.slice(m[0].length) : d.reply).replace(/\*\*/g, '').trim();
				expr = m ? TAGS[m[1]] : 'normal';
				saveHist(text, reply);
			} else [reply, expr] = failLine(d.code);
		} catch (e) {
			[reply, expr] = failLine('error');
		}
		S.busy = false;
		input.disabled = false;
		say(reply, expr, S.chat);
		if (S.chat) input.focus({ preventScroll: true });
	}

	// ---------- 显示 / 躲起来 ----------
	// 访客亲手点过（躲起来 / 叫出来）就记在 localStorage
	function setHidden(on, remember = true) {
		S.hidden = on;
		root.classList.toggle('is-hidden', on);
		cat.setAttribute('aria-label', on ? NAME + '躲起来了，点一下叫出来' : CFG.chat ? NAME + '，点我聊天' : NAME);
		if (remember) safe(() => localStorage.setItem('aipet-hidden', on ? '1' : '0'));
		if (on) {
			setChat(false);
			clearInterval(typeTimer);
			showBubble(false);
			S.talking = false;
			setExpr('sleepy');
		}
	}
	function hop() {
		root.classList.remove('is-hop');
		void root.offsetWidth;
		root.classList.add('is-hop');
	}
	function onCat() {
		if (S.hidden) {
			setHidden(false);
			say(...pickLine(TIPS.back));
			return;
		}
		hop();
		if (CFG.chat) setChat(!S.chat);
		else say(...pickLine(TIPS.poke));
	}

	function mount() {
		if (document.getElementById('aipet')) return;
		root = document.createElement('div');
		root.id = 'aipet';
		root.className = 'aipet';
		root.innerHTML =
			'<div class="aipet-panel">' +
				'<div class="aipet-bubble" role="status" aria-live="polite"></div>' +
				'<form class="aipet-form" autocomplete="off">' +
					'<input type="text" maxlength="200">' +
					'<button type="submit">发送</button>' +
				'</form>' +
				(CFG.notice ? '<p class="aipet-notice">聊天内容会被站长看到</p>' : '') +
			'</div>' +
			'<span class="aipet-fx" aria-hidden="true"></span>' +
			'<button type="button" class="aipet-close" title="躲起来">×</button>' +
			'<div class="aipet-cat" role="button" tabindex="0"></div>';
		document.body.appendChild(root);
		cat = root.querySelector('.aipet-cat');
		R.el.className = 'aipet-sprite' + (R.pixel ? ' is-pixel' : '');
		cat.appendChild(R.el);
		root.style.setProperty('--aipet-w', (CFG.width || 192) + 'px');
		bubble = root.querySelector('.aipet-bubble');
		form = root.querySelector('.aipet-form');
		input = form.querySelector('input');
		fx = root.querySelector('.aipet-fx');
		// 角色名来自后台设置，用属性赋值而不是拼进 HTML
		input.placeholder = '和' + NAME + '聊点什么…';
		input.setAttribute('aria-label', '和' + NAME + '聊天');
		root.querySelector('.aipet-close').setAttribute('aria-label', '让' + NAME + '躲起来');

		cat.addEventListener('click', onCat);
		cat.addEventListener('keydown', e => {
			if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onCat(); }
		});
		cat.addEventListener('pointerenter', () => { S.hover = true; });
		cat.addEventListener('pointerleave', () => { S.hover = false; });
		root.querySelector('.aipet-close').addEventListener('click', () => setHidden(true));
		form.addEventListener('submit', e => {
			e.preventDefault();
			send(input.value.trim());
		});
		input.addEventListener('keydown', e => {
			if (e.key === 'Escape') { setChat(false); cat.focus(); }
		});
		addEventListener('pointermove', e => { mouseX = e.clientX; mouseT = performance.now(); }, { passive: true });
		addEventListener('resize', () => { rect = null; }, { passive: true });
		document.addEventListener('visibilitychange', () => run(!document.hidden));

		// 配色：日间 / 夜间主色来自后台设置；夜间模式按设置识别，切换时说一句
		if (Array.isArray(CFG.colors)) {
			root.style.setProperty('--aipet-c1', CFG.colors[0]);
			root.style.setProperty('--aipet-c2', CFG.colors[1]);
		}
		let dark = isDark();
		root.classList.toggle('is-dark', dark);
		const onTheme = () => {
			const now = isDark();
			if (now === dark) return;
			dark = now;
			root.classList.toggle('is-dark', now);
			if (!S.hidden && !S.chat && !S.busy) say(...pickLine(now ? TIPS.dark : TIPS.light));
		};
		const ob = new MutationObserver(onTheme), watch = { attributes: true, attributeFilter: ['class', ...DARK_ATTRS] };
		ob.observe(document.documentElement, watch);
		ob.observe(document.body, watch);
		safe(() => sysDark.addEventListener('change', onTheme));

		// 访客亲手点过就按访客的；没点过时，窗口窄于设置的宽度（猫会压住侧栏）默认躲着
		const saved = safe(() => localStorage.getItem('aipet-hidden'));
		const narrow = CFG.hideBelow > 0 && matchMedia('(max-width: ' + (CFG.hideBelow - 1) + 'px)').matches;
		setHidden(saved ? saved === '1' : narrow, false);
		setExpr(S.hidden ? 'sleepy' : restExpr());
		run(!document.hidden);
		if (!S.hidden) setTimeout(() => greet(true), 900);
	}

	const later = fn => ('requestIdleCallback' in window ? requestIdleCallback(fn, { timeout: 3000 }) : setTimeout(fn, 1200));
	if (document.readyState === 'complete') later(mount);
	else addEventListener('load', () => later(mount), { once: true });
})();
