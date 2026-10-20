# 发布、私人数据与线上边界

仅在准备版本、发布包或处理私人数据及线上操作时读取本文件。

## 版本与发布包

发布新版本时同步检查：

1. `bangumi-list.php` 插件头中的 `Version`。
2. `BGM_VERSION`。
3. README 中受版本影响的命令和行为。
4. Git tag、Release 名称和发布包目录结构。本仓库放着多个程序,tag 用 `bangumi-list/vX.Y.Z` 前缀。

插件目录名必须保持为 `bangumi-list`。优先发布经过版本化的 Release 包，不把整个
开发仓库直接上传到生产环境。

线上插件目录只包含运行时文件：插件入口、`includes/`、`assets/`、`cli/` 和 `LICENSE`。
不要上传 `.git/`、`data/`、`tools/`、`examples/`、`docs/`、Python 缓存、私人清单
或临时抓图目录。

## 私人和本机数据

`data/` 保存个人清单、导入 JSON、封面、manifest 和历史恢复材料，已由
`.gitignore` 忽略。`covers/`、`anime-list.json`、`examples/*.local.json` 和 Python
缓存也属于本机生成物。

- 不提交这些内容，不加入 Release、部署包、Issue、PR 或公开日志。
- 不在回复中展示个人清单全文或批量输出其内容。
- 默认保留；删除、覆盖、批量重建或对外复制前取得用户明确同意。
- 不在其中保存数据库导出、`wp-config.php`、密码、token、Cookie 或私钥。
- 线上 WordPress 数据库和媒体库是运行时数据源；`data/` 不会自动同步线上状态。
- 封面仅作为个人博客的本地工作资料，版权归各自版权方。

## 生产环境

禁止把 SSH、面板、数据库或 WordPress 密码，API token、Cookie、Authorization
header、`wp-config.php` 内容、SSL 私钥、数据库导出和私人清单写入仓库、命令记录
或最终回复。

生产环境的安装、升级、启停、导入、封面覆盖或数据库写操作必须：

1. 转到对应运维项目并遵守其 `AGENTS.md`。
2. 先做只读检查，确认线上版本和实时状态。
3. 取得用户对线上变更的明确同意。
4. 按运维项目规范创建带 `manifest.txt` 的备份，包含插件目录拷贝和相关 meta 导出。
5. 小步部署并验证 PHP、WordPress、HTTP、日志和磁盘空间。
6. 将部署结果、备份位置和回滚方式写入运维项目的操作日志。

服务器地址、WordPress 根目录、插件部署路径和备份目录属于环境信息，不写入本仓库；
需要时从对应运维项目获取。
