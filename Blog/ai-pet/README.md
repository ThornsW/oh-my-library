# AI 宠物 · 会聊天的看板角色

版本：0.4.1

WordPress 插件：在博客左下角放一个会聊天的看板角色。访客点它就能聊天，它会根据访客正在看的页面和全站文章推荐站内内容。聊天后端可以是任意 OpenAI 兼容接口。角色需要自备，几张图片或一个 JS 角色文件都可以。

> A WordPress plugin that adds a chatty mascot to your blog. It recommends posts from your own site and works with any OpenAI-compatible API. Bring your own character (images or a JS sprite file). UI and prompts are in Chinese.

<p align="center">
  <img src="screenshots/chat-light.png" width="49%" alt="日间：角色推荐文章">
  <img src="screenshots/chat-dark.png" width="49%" alt="夜间配色">
</p>
<p align="center"><sub>日间 / 夜间，图为作者的博客 <a href="https://thornsw.cn">thornsw.cn</a>。图中的像素橘猫是作者自用的角色，<b>不随插件提供</b>。</sub></p>

## 特性

- **站内推荐**：把站点目录（最近 200 篇文章和页面列表）和访客当前所在页面交给模型。角色只推荐本站内容，回答里只有本站链接可以点
- **角色自备**：图片角色会探头、换表情、说话时张嘴；JS 角色可以逐帧画出眨眼、看向鼠标等动画
- **不拖慢网站**：页面加载完、浏览器空闲时才出现
- **适配主题**：自动识别主题的夜间模式，兼容 PJAX 这类无刷新换页
- **不打扰访客**：点 × 后躲起来，只露出头顶；窗口太窄时可以默认躲着
- **后台聊天记录**：按对话查看，可以按 IP 筛选、按关键词搜索，过期自动删除
- **用量可控**：限制每个访客每小时、每天的句数，以及全站每天的总句数，超出后改说预设台词

## 要求

- WordPress 6.5+，PHP 8.0+（已在 WordPress 7.1.3、PHP 8.3 上测试）
- 一个 OpenAI 兼容的聊天接口和 API key，比如 OpenAI、DeepSeek、通义千问的兼容模式，或者自建的 CLIProxyAPI、One API
- 一个角色，见「准备角色」

## 安装

插件目录必须叫 `ai-pet`，只需要 `Blog/ai-pet/plugin/ai-pet/` 这一个目录：

```bash
cp -r Blog/ai-pet/plugin/ai-pet /path/to/wordpress/wp-content/plugins/
```

想在后台「上传插件」里安装，就先打成 zip。不要直接上传整个仓库的「Download ZIP」，那样装不上：

```bash
cd Blog/ai-pet/plugin
mkdir -p ../dist
zip -qr ../dist/ai-pet-0.4.1.zip ai-pet -x "*.md"
```

## 配置

1. 启用插件后，打开后台「AI 宠物 → 设置」
2. **角色**：起个名字，上传图片或放好 JS 角色文件。没有角色时前台什么都不显示
3. **聊天**：填接口地址（写到 `/v1` 为止，如 `https://api.openai.com/v1`）和 API key，保存；然后点「获取模型列表」选一个模型，再保存。建议用回答快的轻量模型
4. 用了页面缓存插件的，清一次缓存

没填 key 时，角色只说预设台词。主色、夜间模式、限额、聊天记录等都在设置页里调。

## 准备角色

插件不带角色，二选一。两者都有时优先用 JS 角色文件。

| | 图片 | JS 角色文件 |
|---|---|---|
| 适合 | 大多数人 | 想要细节动画，愿意自己写或让 AI 写代码 |
| 放在哪 | 设置页里从媒体库选 | 上传到 `wp-content/uploads/ai-pet/character.js` |

想先看看效果：把 [`examples/character.example.js`](examples/character.example.js)（一个方块脸角色）上传到上面的位置就能用。

### 图片

- 至少要一张「普通」图。可选的还有开心、害羞、惊讶、困了、说话（张嘴）、眨眼（闭眼），没提供的都用「普通」图
- 用透明背景的 PNG / WebP / GIF。**所有图的画布大小和角色位置都要一样**，角色下半身贴着图片底边，看起来像从屏幕底下探出头
- 画布接近正方形就行，如 512×464；如果是像素画，在设置里勾上「像素画」

可以用 AI 画图工具生成：先出一张「普通」图，再用「保持角色一致」的功能逐张改表情。提示词示例：

```
Q 版的<你的角色>，从画面底边探出头和两只前爪，正面看向镜头，<画风>，透明背景，正方形画布，角色居中。
```

### JS 角色文件

在 JS 文件里定义 `window.AIPET_CHARACTER`，然后用 FTP、SSH 或主机面板的文件管理器上传到 `wp-content/uploads/ai-pet/character.js`（媒体库默认不让传 `.js`）。放在 uploads 里，更新插件时不会被覆盖；改了文件，浏览器缓存会自动刷新。

```js
(function () {
  window.AIPET_CHARACTER = {
    width: 64, height: 58,     // 画布的像素尺寸；显示时按「显示宽度」等比放大
    pixelated: true,           // 放大时保持像素锐利（默认 true）
    rise: { up: -3, down: 4 }, // 可选：探出头 / 趴着时，整体下移几个像素。引擎会在两者之间做动画，再叠加 1 像素的呼吸起伏

    // 画一帧。ctx 是 width×height 的 2D 画布，已经清空。
    // 同样的状态只画一次，引擎会缓存起来，所以这里可以慢慢逐像素画。
    draw(ctx, s) {
      // s.expr   'normal' | 'happy' | 'shy' | 'surprised' | 'sleepy'
      // s.blink  true 时闭眼（眨眼）
      // s.talk   true 时张嘴（说话时来回切换）
      // s.look   -1 / 0 / 1：鼠标在左边 / 正前方 / 右边，可以让眼珠跟着动
      // s.ear    0–3：抖耳朵动画的帧，0 表示不抖
      // s.rise   整体下移的像素数，在 rise.up 到 rise.down + 1 之间
    },

    // 可选：覆盖预设台词。每项是若干条 [文字, 表情]，随机挑一条。
    // 占位符：{name} 角色名，{site} 站名，{t} 文章标题（只在 post 里有）
    // 键：home 首页、post 文章页、anime 看番页、other 其他页、night 深夜第一次打招呼、
    //     dark / light 切换夜间 / 日间、poke 没开聊天时被点、idle 闲着、back 躲起来后被叫出来、chat 打开聊天框
    lines: {
      home: [['欢迎来到「{site}」～点我可以聊天汪！', 'happy']],
    },
    // 可选：覆盖出错时的台词，每项一条 [文字, 表情]
    // 键：limit 超出限额、off 聊天没开、bad 消息太长、forbidden 外站请求、error 接口出错
    fail: {
      limit: ['今天聊得太多啦，{name}要去睡觉了……', 'sleepy'],
    },
  };
})();
```

也可以让 AI 来写：把下面这段要求连同上面的接口说明一起发给 ChatGPT、Claude 等，先用它给的预览页检查效果，满意了再上传。

```
请帮我写 WordPress 插件「AI 宠物」用的 JS 角色文件 character.js，接口说明附后。要求：
1. 只用原生 JavaScript，整个文件包在立即执行函数里，最后给 window.AIPET_CHARACTER 赋值。
2. 角色：<描述你的角色，例如：戴蓝色围巾的白色小狗，像素风，64×58，从画面底边探出头和两只前爪>。
3. 用 ctx.fillRect 逐像素作画。五种表情要一眼能分清，并支持 s.blink、s.talk、s.look、s.ear、s.rise。
4. 按角色性格写一套 lines 和 fail 台词。
5. 另外给一个 HTML 预览页，能切换上面所有状态。
```

**JS 角色文件会在每个前台页面上执行**，只放你自己写的或检查过的代码。

## 聊天记录与隐私

开启聊天记录后，发给模型的每句话都会存进表 `wp_aipet_log`，内容包括时间、访客 IP（或匿名编号）、所在页面、模型和问答内容。

<p align="center"><img src="screenshots/admin-log.png" width="80%" alt="后台聊天记录"></p>
<p align="center"><sub>后台「AI 宠物 → 聊天记录」（演示数据）</sub></p>

**默认会记录 IP 原文，而且不提示访客。** IP 和聊天内容属于个人信息，请按你所在地区的法规（如《个人信息保护法》、GDPR）决定：要不要记录、要不要记 IP、要不要提示访客。这三项都能在设置里改。

## 安全

- API key 只在服务器端使用，不会出现在页面、接口响应和提示词里
- 模型没有任何操作能力，只能回复文字；回答按纯文本显示，只有本站链接可以点
- 模型只能看到公开的文章和页面
- 聊天接口会检查请求来源，并按 IP 和全站限额。来源可以伪造，真正兜底的是限额：最坏情况是当天额度被用完

## 常见问题

**前台看不到角色？** 还没设置角色。设置好后清一次页面缓存。

**改了设置，前台没变？** 清一次页面缓存。

**网站用了 Cloudflare 或其他 CDN？** 把「访客 IP 来源」改成对应的选项，否则所有访客都会被当成同一个 IP。没经过对应代理时不要改，否则访客能伪造 IP 绕过限额。

**角色挡住了侧栏？** 调大「窗口窄于多少 px 时默认躲起来」，或者调小「显示宽度」。

**卸载会删掉什么？** 「停用」不删任何东西。在后台「删除」插件时，会删掉聊天记录、设置和 API key；`uploads/ai-pet/` 里的角色文件不会删。

**会用掉多少 token？** 每句话的输入约等于人设 + 站点目录 + 最近 6 轮对话。60 篇文章左右的博客，每句约 7,800 tokens，回答一般不到 300 tokens。可以用「全站每天句数」控制总量。

## 已知问题

- 聊天记录按「浏览器标签页 + IP」分组，访客中途换了 IP 会显示成两段
- 回答里的站内链接显示成网址路径，而不是文章标题
- 界面、台词和提示词都是中文

## 看番清单联动

同时装了 [Bangumi List 看番清单](https://github.com/ThornsW/oh-my-library/tree/master/Blog/bangumi-list) 时，角色也能推荐番剧，访客打开看番页时会说专门的台词。

## 许可

[GPL-2.0-or-later](LICENSE)
