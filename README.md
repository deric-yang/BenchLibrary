# KW Bench Library

KW Bench Library 是面向知识工作与 Office / Web 产物评测的公开浏览站。它把 Benchmark 从一个名字展开为可搜索的任务、附件、参考产物、Verifier 设计和 Verifier 源码，并提供中英文切换与安全的站内预览。

公网入口：<https://benchlibrary.com>

## 发布架构

```text
benchlibrary.com
  Cloudflare Worker
  └─ /site/*、/data/* 与 /assets/*（同一不可变 release，同源流式读取 R2）

开发机 immutable release
  └─ 公开策略白名单导出 + 脱敏 + SHA-256 manifest
       └─ R2 releases/<release-id>/...
```

每次发布使用不可变 `release-id`。数据完整上传和核验后，只修改 Worker 的 `PUBLIC_RELEASE_ID` 即可原子切换；不会覆盖上一版对象。

## 公网边界

公网导出是显式白名单，不是开发机目录的镜像：

- 完整发布 30 个已确认可公开再分发的 Benchmark，共 10,161 个任务。
- 每个 Benchmark 的 `full`、`metadata_only`、`link_only` 或 `exclude` 决策都在固定策略中逐项记录；不依据 gated 状态或其他单一信号自动推断。
- 未取得最终公开发布确认、禁止再分发以及 proprietary / closed Benchmark 仍保持链接、元数据或完全排除边界。
- 永不打包接入后台、Contributor Key、Hugging Face Token、作业记录、私有 corpus、服务端配置或内部部署清单。
- 原始 HTML、JavaScript、SVG 与 Verifier 源码由 Worker 强制按文本提供；转换后的 HTML 预览在无同源权限、无网络能力的 sandbox 中打开。
- 固定 revision 中已经由上游发布、但结构本身不完整的对象必须按 path、size 与 SHA-256 精确登记并在页面显式提示；无效归档只允许作为下载附件提供。

具体决策见 [`config/publication_policy.json`](config/publication_policy.json)。上游数据和产物继续适用各自许可证；本仓库的 Apache-2.0 许可证不会覆盖它们。

开发机版本与公网版本的来源、同步、核验、切换和回滚约定见 [`docs/RELEASE_RUNBOOK.md`](docs/RELEASE_RUNBOOK.md)。

## 本地开发

需要 Node.js 22+ 与 Python 3.9+。

```bash
npm ci
python3 scripts/build_public_ui.py
npm run check
npm run deploy:dry-run
```

`scripts/build_public_ui.py` 从内部看板源生成纯公开 UI，并在构建时断言接入表单和凭据相关字符串均不存在。不要手工把内部 `index.html`、`app.js` 或 `ingestion.js` 复制到 `site/`。

## 生成公开数据版本

在持有 immutable 内部 release 的机器上执行：

```bash
python3 scripts/export_public_release.py \
  --source /path/to/immutable-release \
  --destination /path/to/public-releases/<release-id> \
  --policy config/publication_policy.json \
  --release-id <release-id> \
  --site-dir site
```

导出器会验证题目数及策略中固定的源分片 SHA-256、递归解析本地依赖、阻断跨 Benchmark 引用、路径逃逸和符号链接，对 JSON 敏感字段脱敏，并扫描原始文件及 ZIP/Office/Gzip 压缩内容中的强凭据特征。每个发布对象都会写入 SHA-256 manifest。源文件和目标文件必须位于同一文件系统，导出器通过 hard link 避免额外占用同等体积的磁盘空间。

## 部署

日常部署使用项目固定的 Wrangler 版本：

```bash
KWBL_PUBLIC_RELEASE_ID=<validated-release-id> npm run deploy
```

大体积数据必须先完成本地逐文件哈希复验、R2 上传与远端 inventory 校验，再切换 `PUBLIC_RELEASE_ID`。上传器会核对 manifest 中每个 `r2_key` 和临时端点的 immutable release 前缀，断点命中也不会跳过本地内容复验；断点状态保存在 release 目录之外。`ops/uploader-worker.mjs` 是仅用于首次/批量传输的临时、前缀受限上传器；它使用一次性随机密钥，传输完成后应删除 Worker 和密钥文件，不能作为生产写入口保留。

任何凭据只能通过 Cloudflare secret、短时会话或权限收敛的本机文件注入，不能写入 Git、发布 manifest、浏览器存储或日志。

## 协作约定

新增 Benchmark 时，请同时提交：

1. 官方仓库、数据集或论文入口，以及固定 revision。
2. 数据许可证、代码许可证和原件再分发依据。
3. 任务字段、附件、Gold/参考产物与 Verifier 的映射说明。
4. 期望任务总数和全量校验依据。
5. 公开策略变更与对应测试。

发布脚本对未出现在策略中的 Benchmark 会 fail closed，避免新接入内容未经许可审计就进入公网版本。
