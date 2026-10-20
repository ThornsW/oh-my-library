# week-plan · 周计划

版本：0.3.0

WordPress 插件：把待办按天排进一周的计划表。界面在 wp-admin 后台，单用户使用。

## 它解决什么

普通待办清单只回答「有什么要做」，不回答「哪天做」。week-plan 把两者分开：

- **待办**：一件要做的事，可以有截止日
- **排期**：「某个待办 × 某一天」。一个待办可以排进任意多天，日期不必连续，长期计划就是一串排期
- 每一天单独打勾，整个待办另外「结项」

每周花一点时间，把待办从侧栏拖进下周的具体日子，这就是全部的用法。

## 要求

- WordPress 6.0+（在 7.0 上测试过），PHP 8.1+
- 桌面浏览器：拖拽用的是浏览器原生拖拽，手机上用不了
- 只有管理员能看到「周计划」菜单

## 安装

插件代码在 `Blog/week-plan/plugin/week-plan/`，目录名必须保持 `week-plan`。不要拷 `.md` 文件，Web 服务器会把它们原样公开：

```bash
rsync -a --exclude='*.md' Blog/week-plan/plugin/week-plan/ /path/to/wordpress/wp-content/plugins/week-plan/
```

想在后台「上传插件」里安装，就先打成 zip，顶层目录必须是 `week-plan/`：

```bash
cd Blog/week-plan/plugin
zip -qr ~/week-plan-0.3.0.zip week-plan -x "*.md"
```

在后台「插件」里启用「周计划」。启用时会自动建一张排期表 `<表前缀>weekplan_schedule`。

## 用法

后台左侧菜单「周计划」，分三栏：

- **左栏**：待办清单。顶部是上周没做完的「逾期」，底部折叠起来的是还没排期的「未来计划」。可以按标签筛选或分组
- **中栏**：本周 7 天。从左栏拖到某天就是排期；在中栏里拖到另一天是改期，拖出中栏是取消这一天的排期
- **右栏**：编辑选中的待办，包括标题、Markdown 笔记、截止日、优先级、标签、子任务；下方是一张常驻便签
- 右键菜单里有「整体顺延」等操作；「批量排期」可以一次排一个日期区间里指定的星期几
- 「规划下周」按钮直接跳到下周

一周从哪天开始，跟随 WordPress「设置 → 常规 → 一星期开始于」；「今天」按站点时区计算。

**可选字体**：界面优先用 Maple Mono NF CN。插件不打包字体文件，站点的 `wp-content/uploads/fonts/` 下有 `MapleMono-NF-CN-Regular.woff2` 和 `MapleMono-NF-CN-Bold.woff2` 时会自动使用，没有就用系统等宽字体。

## 文档

- [设计规格](docs/design-spec.md)：已确认的设计决定和理由
- 第三方代码见 `plugin/week-plan/vendor/README.md`

## 许可证

GPL-2.0-or-later，详见 [LICENSE](LICENSE)。内置的 Parsedown 1.8.0 是 MIT 许可，原文在 `plugin/week-plan/vendor/Parsedown-LICENSE.txt`。
