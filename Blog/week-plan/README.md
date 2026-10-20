# week-plan · 周计划

版本：0.3.0

一个 WordPress 插件，把待办按天排进一周的计划表里。界面在 wp-admin 后台，单用户。

它取代旧的 Memo 桌面应用（本仓库的 `Tools/Memo/`），但不是它的新版本：无共享代码、无数据迁移、不同运行形态。

## 它解决什么

普通待办清单只回答「有什么要做」，不回答「哪天做」。长期计划（比如一项持续三个月的学习）在清单里只是一条永远做不完的项目。

week-plan 把这两件事分开：

- **待办**是一件要做的事，可以有截止日，但那不等于你打算哪天做它。
- **排期**是「某待办 × 某一天」的记录。一个待办可以排到任意多天，日期不必连续。长期计划就是一堆排期。
- 每一天单独打勾，整个待办另有一个「结项」。做了多少天一目了然。

每周花一小段时间，把待办从侧栏拖进下周的具体某天，就是全部的工作流。

## 要求

- WordPress 6.0+（用到的 WordPress 函数 5.3 起就有；因为插件要求 PHP 8.1，最低写 6.0。实际只在 7.0 上测试过）
- PHP 8.1+
- 桌面浏览器：拖拽用的是浏览器原生拖拽，手机上不能用
- 只有管理员（`manage_options` 权限）能看到「周计划」菜单

## 安装

插件代码在 oh-my-library 仓库的 `Blog/week-plan/plugin/week-plan/`，目录名必须保持 `week-plan`。

```bash
rsync -a --exclude='*.md' Blog/week-plan/plugin/week-plan/ /path/to/wordpress/wp-content/plugins/week-plan/
```

不拷 `.md`：Nginx 等 Web 服务器会把站点目录里的非 PHP 文件原样公开。

想在后台「插件 → 安装插件 → 上传插件」里装，就先打成 zip（顶层目录必须是 `week-plan/`）：

```bash
cd Blog/week-plan/plugin
zip -qr ~/week-plan-0.3.0.zip week-plan -x "*.md"
```

装好后在后台「插件」里启用「周计划」。启用时会自动建一张排期表 `<表前缀>weekplan_schedule`（默认前缀下是 `wp_weekplan_schedule`）。

## 用法

后台左侧菜单「周计划」，三栏布局：

- **左栏**：待办清单。顶部是上周没做完的「逾期」，底部折叠的「未来计划」是还没排期的待办。可以按标签筛选，也可以按标签分组。
- **中栏**：本周 7 天。把左栏的待办拖到某一天就是排期；在中栏里拖到另一天是改期，拖出中栏是取消这一天。每张卡片单独打勾。
- **右栏**：选中待办后编辑标题、Markdown 笔记、截止日、优先级、标签、子任务；下面常驻一张随手记的便签。
- 右键菜单里有「整体顺延」「取消这一天的排期」等；「批量排期」可以一次排一个日期区间里的指定周几。
- 「规划下周」按钮一键跳到下周，专心排期。

一周的起始日跟随 WordPress「设置 → 常规 → 一星期开始于」，「今天」按站点时区计算。

### 可选：字体

界面优先用等宽字体 Maple Mono NF CN。插件不打包字体文件（约 12 MB）：如果站点的 `wp-content/uploads/fonts/` 下有 `MapleMono-NF-CN-Regular.woff2` 和 `MapleMono-NF-CN-Bold.woff2`，就自动使用；没有就用系统等宽字体，不影响功能。

## 文档

- [设计规格](docs/design-spec.md)：35 个已确认的设计决定及其理由，实现以此为准。
- 第三方代码见 `plugin/week-plan/vendor/README.md`。

## 目录

```
plugin/week-plan/   插件源码，部署时只拷这个目录
docs/               设计文档
```

## 许可证

GPL-2.0-or-later，详见 [LICENSE](LICENSE)。内置的 Parsedown 1.8.0 是 MIT 许可，原文见 `plugin/week-plan/vendor/Parsedown-LICENSE.txt`。
