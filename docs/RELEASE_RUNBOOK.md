# KW Bench Library 发布与维护手册

本文约定两个明确分离的版本：

- **开发机版本**：位于开发机 `/mnt/data/projects/bench-monitor`，包含完整内部目录、接入工作区、物化语料和 immutable release。它是公网数据的唯一上游来源，但不是可直接发布的目录。
- **公网版本**：由 GitHub `main` 上的公开代码与策略、R2 中不可变的数据版本，以及 Worker 当前指向的 `PUBLIC_RELEASE_ID` 共同构成。公网大文件只存储在 R2，不回传或常驻本地 Mac。

GitHub `main` 是公网代码、导出器、发布策略和运行手册的事实来源；开发机 immutable release 是任务、原件、预览和 verifier 数据的事实来源。R2 是经过筛选和校验的发布副本，不能反向覆盖开发机数据源。

## 版本流向

```text
GitHub main（代码、策略、Worker）
                  +
开发机 immutable release（完整数据源）
                  │
                  ▼
public exporter（白名单、脱敏、引用闭包、SHA-256）
                  │
                  ▼
开发机 public-releases/<release-id>（不可变候选版本）
                  │
                  ▼
R2 releases/<release-id>/（完整 inventory 复验）
                  │
                  ▼
Worker PUBLIC_RELEASE_ID 原子切换 ──失败──▶ 切回上一 release-id
```

开发机看板的日常改动不会自动进入公网。只有完成下列整套流程并切换 Worker 指针后，公网才会更新。

## 发布前提

1. 从 GitHub `main` 创建全新、干净的工作目录；不要以本地 Mac 上陈旧或有未提交修改的副本作为发布源。
2. 在开发机冻结一个新的 immutable release，并记录其绝对路径与生成 revision。
3. 对准备公开的每个 Benchmark 确认固定 revision、期望任务数以及分片 SHA-256；把这些值写入 `config/publication_policy.json`。
4. 原样保留上游许可证、署名、NOTICE 和原件来源信息。中文翻译、格式转换及安全预览必须注明为修改或派生内容，不得让本仓库的 Apache-2.0 许可证覆盖上游内容。
5. 当前策略中的 GDPval、OfficeQA Full / Pro V2、WorkBuddyBench Office、ArtifactsBench 和 GameCraft-Bench，均按最终公开发布确认进入 `full`；发布时仍须保留各自固定 revision 和上述归属信息。GameCraft-Bench 只发布固定仓库 revision 内的 140 个官方任务，排除 `tasks/example`，不执行上游脚本，也不镜像仓库外第三方素材池或演示站产物。
6. 若固定 revision 的上游对象本身存在结构缺损，只能在 `upstream_integrity_exceptions` 中按路径、字节数与 SHA-256 精确登记。无效归档仅作为附件下载；截断媒体必须显示上游异常提示，不能伪装成完整预览。异常字节变化、恢复为可解析归档或离开公开闭包都会使导出失败。

## 标准发布流程

以下命令应在开发机的干净 GitHub 工作区执行。变量名仅作示例，应为每次发布设置具体值：

```bash
KWBL_SOURCE_RELEASE="/mnt/data/projects/bench-monitor/releases/<immutable-release>"
KWBL_PUBLIC_RELEASE_ID="<yyyyMMddTHHmmssZ-public-vN>"
KWBL_PUBLIC_RELEASE="/mnt/data/projects/bench-monitor/public-releases/$KWBL_PUBLIC_RELEASE_ID"
KWBL_INTERNAL_UI="/mnt/data/projects/bench-monitor/current"
KWBL_UPLOAD_ENDPOINT="https://<temporary-uploader-host>"
KWBL_UPLOAD_TOKEN_FILE="/path/to/restricted/one-time-token"
KWBL_NETWORK_PROXY="http://agent.baidu.com:8891"
KWBL_COPY_SOURCE_MANIFEST="/mnt/data/projects/bench-monitor/public-releases/<previous-release>/data/public_manifest.json"
```

先构建公开 UI，并运行代码测试：

```bash
python3 scripts/build_public_ui.py \
  --source "$KWBL_INTERNAL_UI" \
  --output site
npm ci
npm run check
python3 -m unittest discover -s tests
npm run deploy:dry-run
```

再对源版本做策略和引用闭包校验。两种校验都必须通过：

```bash
python3 scripts/export_public_release.py \
  --source "$KWBL_SOURCE_RELEASE" \
  --policy config/publication_policy.json \
  --release-id "$KWBL_PUBLIC_RELEASE_ID" \
  --validate-only

python3 scripts/export_public_release.py \
  --source "$KWBL_SOURCE_RELEASE" \
  --policy config/publication_policy.json \
  --release-id "$KWBL_PUBLIC_RELEASE_ID" \
  --validate-closure
```

### 仅用于历史公开原件缺洞的 composite 恢复

如果新的开发机 immutable release 缺少一个已经在上一版公网 release 完整发布、并经 R2 inventory
核验的历史原件，`validate-only` 或 `validate-closure` 会按缺失路径失败。此时不得修改 immutable
release，也不得重新从上游猜测下载；可以创建一个隔离、base-first 的 composite 审计源：

```bash
KWBL_CANONICAL_SOURCE="/mnt/data/projects/bench-monitor/releases/<immutable-release>"
KWBL_PREVIOUS_PUBLIC_RELEASE="/mnt/data/projects/bench-monitor/public-releases/<previous-release>"
KWBL_PREVIOUS_R2_INVENTORY="/mnt/data/projects/bench-monitor/public-releases/.<previous-release>.r2-inventory.json"
KWBL_COMPOSITE_SOURCE="/mnt/data/projects/bench-monitor/public-source-composites/<new-composite-id>"

python3 scripts/build_public_composite_source.py \
  --base-root "$KWBL_CANONICAL_SOURCE" \
  --overlay-root "$KWBL_PREVIOUS_PUBLIC_RELEASE" \
  --overlay-inventory "$KWBL_PREVIOUS_R2_INVENTORY" \
  --policy config/publication_policy.json \
  --output-root "$KWBL_COMPOSITE_SOURCE" \
  --execute
```

该恢复流程只适用于“当前 immutable 缺洞、上一版公网已有且 inventory 已核验”的对象，不是通用
数据合并器。builder 会完整绑定 base `release_manifest.json`、上一版 `data/public_manifest.json`
及其同名 R2 inventory；只允许从上一版补入当前缺失的 `assets/mirrors/`、`assets/previews/`
和 `assets/verifiers/` 文件。`data/**`、`site/**`、`assets/index_shards/**`、三个 root index
以及其他 asset namespace 都不会从旧版继承。当前 base 已有的文件永不覆盖；同路径异字节时保留
base，并将双方实际 size/SHA-256 与 `base_retained` 决策写入 provenance。

输出必须是全新、非 `current`、非 `live`、非 `releases` 的目录。完成标记和每个补入对象的
path/size/SHA-256/transfer、两份 manifest 哈希、R2 inventory 哈希与摘要、策略哈希、跳过与冲突
统计均写入 composite 根目录的 `.kwbl-composite-provenance.json`（`0644`）；该顶层文件不进入
公网引用闭包。composite 只是一次公网导出的开发机审计源，不替代 canonical immutable release，
也不能反向覆盖开发机 `current`。

构建完成后，将本次命令的 `--source` 指向 `$KWBL_COMPOSITE_SOURCE`，重新运行原版 exporter 的
`--validate-only` 与 `--validate-closure`。两项必须都通过；若当前 root index 指向缺失的 hashed
index shard，或仍有任何未被严格允许的缺口，应继续 fail closed，不能从旧版偷补。最终公开候选
仍须由 exporter 新建到 `public-releases/<release-id>`，不得直接发布 composite。

校验通过后，生成与源版本位于同一文件系统的公开候选版本。导出器使用 hard link 节省开发机空间：

```bash
# 常规发布使用 immutable release；composite 恢复场景必须显式改为 "$KWBL_COMPOSITE_SOURCE"。
KWBL_PUBLIC_EXPORT_SOURCE="$KWBL_SOURCE_RELEASE"

python3 scripts/export_public_release.py \
  --source "$KWBL_PUBLIC_EXPORT_SOURCE" \
  --destination "$KWBL_PUBLIC_RELEASE" \
  --policy config/publication_policy.json \
  --release-id "$KWBL_PUBLIC_RELEASE_ID" \
  --site-dir site
```

核验 `data/public_manifest.json` 中的 release id、策略 id、Benchmark 数、任务数、文件数、字节数与 SHA-256。候选版本生成后不得在原目录内修改；任何变更都要生成新的 release id。

## R2 上传与完整性核验

为本次 release 创建临时、仅允许写入 `releases/<release-id>/` 的上传端点和一次性随机密钥。使用 `ops/wrangler.uploader.jsonc`，把 `UPLOAD_PREFIX` 固定为新 release，把 `COPY_SOURCE_PREFIX` 固定为上一个已通过完整 inventory 核验的 release。密钥只能通过权限收敛的文件传入，不得写入 Git、manifest、日志或浏览器存储。

密钥文件必须位于开发机、权限为 `0600`，并保存至少 32 字节的随机值。上传客户端会对文件内容执行
`.strip()` 后再发送，因此写文件时不要保留末尾换行，或在计算 `UPLOAD_KEY_SHA256` 时对同一个去除首尾空白后的
值计算 SHA-256；不能直接对带换行的文件做哈希。Cloudflare 配置和发布记录中只允许出现该 SHA-256，不能
出现原始密钥。

若临时端点复用生产域名，只挂载精确的 HTTPS path route
`https://benchlibrary.com/_kwbl-upload/*`；不要创建无 scheme、全站或通配子域路由。上传前先验证无密钥访问返回 404、带密钥 health 返回精确新旧 prefix；清理时先删除这条 route，再删除临时 Worker。

若通过 Cloudflare API / MCP 直接上传临时 Worker，`ops/wrangler.uploader.jsonc` 中的
`workers_dev=false` 与 `preview_urls=false` 不会自动成为 API 请求的一部分。Worker 模块上传成功后、创建
path route 之前，必须调用该 Worker 的 subdomain API，将 `enabled` 和 `previews_enabled` 同时设为
`false`，并读取返回值确认两者均为 `false`。任一步失败都应先删除临时 Worker，不能继续挂路由。这样临时
写入口只存在于上述精确 HTTPS path，不会额外暴露在 `workers.dev` 或版本预览地址上。

上传器可以复用旧 release 中**相同相对路径、相同字节数、相同 SHA-256** 的对象。客户端先重新读取并哈希新候选文件，再依据旧 manifest 决定是否请求复用；临时 Worker 仍会对固定旧 prefix 下的对象重新检查 size、SHA-256 metadata 和 ETag，并用 R2 binding 在 Cloudflare 内部流式写入新 prefix，同时让 R2 校验 SHA-256。任何不匹配项都会自动回到原有直传/分段上传路径。这个优化不改变最后的逐对象 inventory 核验，也不允许跨出固定新旧 release prefix。

```bash
python3 scripts/upload_public_release.py \
  --root "$KWBL_PUBLIC_RELEASE" \
  --endpoint "$KWBL_UPLOAD_ENDPOINT" \
  --token-file "$KWBL_UPLOAD_TOKEN_FILE" \
  --copy-source-manifest "$KWBL_COPY_SOURCE_MANIFEST" \
  --proxy "$KWBL_NETWORK_PROXY" \
  --workers 12 \
  --delete-token-on-success
```

若 Cloudflare 内部复用在真实环境中持续失败，保持同一个新 release 与断点文件，去掉 `--copy-source-manifest` 后重跑即可全量直传；不要放宽 prefix、路径、SHA 或 inventory 校验来换取复用成功。

上传器支持断点续传，并在结束时抓取完整 R2 inventory。切换前必须再做一次离线一一对应核验，包括 key、size、SHA-256 custom metadata 及 Content-Type、Cache-Control、Content-Encoding、Content-Disposition HTTP metadata：

```bash
python3 scripts/verify_r2_release.py \
  --manifest "$KWBL_PUBLIC_RELEASE/data/public_manifest.json" \
  --inventory "/mnt/data/projects/bench-monitor/public-releases/.$KWBL_PUBLIC_RELEASE_ID.r2-inventory.json"
```

只有当对象 key 集合、文件数、总字节数、逐文件大小和 SHA-256 metadata 全部精确一致时，才能继续。上传成功后立即删除临时上传 Worker、临时域名和残余密钥文件；生产环境不保留写入口。

## Worker 切换、验收与回滚

先记录线上旧的 `PUBLIC_RELEASE_ID`、当前 deployment id 和其 100% 流量对应的 Worker
version id。后者是包含旧代码、静态资源、bindings 与旧 release 指针的精确回滚锚点；不要只记
release id。再把 Worker 指向已通过 inventory 核验的新版本：

```bash
KWBL_PUBLIC_RELEASE_ID="$KWBL_PUBLIC_RELEASE_ID" npm run deploy
```

切换后以未登录、无 Cookie 的客户端检查：

- 首页、目录、任务搜索和中英文切换可用；
- GDPval、OfficeQA Full / Pro V2、WorkBuddyBench Office、ArtifactsBench、GameCraft-Bench 的任务数与策略一致；
- 每类任务至少抽查题面、输入附件、Gold/参考产物、Verifier 设计、Verifier 源码和原件内嵌预览；
- `/data/*`、`/assets/*` 返回同一 release，原始 HTML/JavaScript/SVG/源码以文本或隔离安全预览提供；
- 不出现登录页、Contributor Key、Hugging Face Token、内部路径、作业记录或服务端配置。

先运行仓库内的匿名只读 smoke。它不会携带 Cookie 或凭据，也不会调用 Cloudflare 写接口；8 个既有
小型代表原件/预览与 7 个从已固定 GameCraft task shard 动态解析出的 Gold、GDScript、solve.sh、
安全预览和 Verifier 源码会完整下载并复算 SHA-256，4 个已固定的上游异常对象仅用 Range 校验：

```bash
python3 scripts/smoke_public_release.py \
  --base-url https://benchlibrary.com \
  --expected-release-id "$KWBL_PUBLIC_RELEASE_ID"
```

需要从开发机经显式公网代理执行时追加 `--proxy http://agent.baidu.com:8891`。脚本退出码非零即视为
验收失败；浏览器人工检查负责补充搜索、Tab 切换与内嵌预览的交互验收。

如任一项失败，不覆盖或删除新旧 R2 对象，直接把流量回滚到发布前记录的精确 Worker
version。这样代码、静态资源和 `PUBLIC_RELEASE_ID` 会一起恢复，不会用“新代码 + 旧数据指针”
拼出一个从未验收过的组合：

```bash
KWBL_PREVIOUS_WORKER_VERSION="<previous-100-percent-version-id>"
npx wrangler rollback "$KWBL_PREVIOUS_WORKER_VERSION" \
  --name kw-bench-library \
  --message "Rollback failed public release smoke test"
```

回滚后修复问题并生成新的 release id，不能原地修改失败版本。旧版本至少保留到新版本通过完整验收；后续清理须依据 R2 inventory 和发布记录精确指定 release 前缀。

## 日常协作规则

- 看板功能、翻译、任务映射或物化数据先在开发机版本完成；公网同步必须走本手册全流程。
- 公网代码改动通过 GitHub `main` 协作；大文件不提交 Git，只经 exporter 进入 R2。
- 每次发布记录 Git commit、源 immutable release、policy id、公开 release id、R2 inventory 摘要、旧/新 Worker 指针和验收结果。
- 同事新增 Benchmark 时，应提交固定来源 revision、字段映射、期望任务数、分片 SHA、署名/许可/NOTICE 与修改说明；策略未显式列出的内容继续 fail closed。
