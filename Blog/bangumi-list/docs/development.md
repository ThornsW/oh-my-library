# 开发与验证

仅在修改实现、工具或测试行为时读取本文件。

## 代码结构

- `bangumi-list.php`：插件入口、CPT、后台字段、保存逻辑和 WordPress 接线。
- `includes/helpers.php`：纯函数和可独立验证的逻辑。
- `includes/class-bgm-fetcher.php`：封面搜索、校验和媒体库导入。
- `includes/render.php`：短代码查询与 HTML 渲染。
- `cli/import-command.php`：`wp bangumi ...` 命令。
- `assets/`：作用域化 CSS 和原生 JavaScript。
- `tools/`：本机维护工具。
- `examples/`：公开示例和格式转换示例。
- `docs/`：项目文档和公开截图。
- `data/`：被忽略的本机私人数据，不属于源码或发布物。

保持这些职责边界，不在插件仓库中加入服务器运维实现。

## 实现约定

- 全局 PHP 函数、类、常量、过滤器和资源句柄使用 `bgm_`、`BGM_` 或
  `bangumi_list_` 前缀。
- 保持 PHP 7.4 和 WordPress 5.8 兼容，不使用更高版本才支持的语法或 API。
- WordPress 输入执行 nonce、权限、`wp_unslash()` 和相应的 sanitize 检查。
- HTML、属性和 URL 输出使用对应的 escaping 函数。
- 数据库和媒体库操作使用 WordPress API，不直接拼接 SQL。
- 外部下载使用 HTTPS、合理超时、文件类型与封面比例校验；manifest 路径限制在
  指定目录内，避免路径穿越。
- CSS 限定在 `.bgm-*` 范围内；资源仅在短代码实际渲染时加载。
- 前端继续使用原生 JavaScript。引入构建链或第三方运行时依赖前说明必要性。
- 抓取 Bangumi 或蜜柑数据时保留明确的 User-Agent 和限流，请求间隔不得低于
  0.3 秒。
- 用户可见行为、短代码属性、WP-CLI 参数或数据格式改变时同步更新 README。

## Python 环境

本机使用 Miniforge/mamba，不向 `base` 安装项目依赖。

- `tools/fetch-covers-local.py` 和 `tools/fetch-links-local.py` 使用 Python 3.7+
  标准库。
- `examples/xlsx_to_json.py` 依赖 `openpyxl`。
- 默认用 miniforge 的 `GeneralDev` 环境，依赖清单见 `requirements.txt`。

## 验证

按改动范围执行最小充分验证。

PHP 修改：

```bash
find . -path './data' -prune -o -name '*.php' -print0 | xargs -0 -n1 php -l
```

前端 JavaScript 修改：

```bash
node --check assets/anime.js
```

Python 修改需要先确认并激活项目环境，然后执行：

```bash
python -m py_compile tools/fetch-covers-local.py tools/fetch-links-local.py examples/xlsx_to_json.py
```

当前没有自动化测试框架。涉及核心行为时重点检查：

- 插件可以启用，没有 PHP warning 或 fatal。
- `[anime_list]` 能渲染空清单、有封面及无封面的条目。
- 搜索、两种排序和移动端点按交互正常。
- 后台保存继续执行 nonce、权限和数据清洗。
- 评分解析兼容纯数字、`x/10`、空值和自由文本。
- 封面比例、最小宽度、失败回退及源文件保留逻辑正确。

对 `wp bangumi normalize-ratings` 和 `wp bangumi import-covers` 先使用
`--dry-run`。`wp bangumi import`、`wp bangumi fetch-covers` 及其他没有 dry-run
的写命令不得直接在生产环境试验。
