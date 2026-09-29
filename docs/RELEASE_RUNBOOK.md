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

## 凭据模型与无人值守边界

发布凭据分为互不复用的两层，任何一层都不得以“永久 Token”形式硬编码进代码、Git 历史、命令行参数、
环境变量、日志、发布 manifest 或浏览器存储：

- **Mac 控制面**只负责创建/删除临时 Worker、精确 path route 和切换正式 Worker 版本。持久授权应使用
  Cloudflare OAuth refresh credential；首次人工授权完成后，refresh credential 只保存在 macOS Keychain，
  短时 access token 只存在于刷新进程内存中。控制面请求通过显式代理
  `http://agent.baidu.com:8891` 发出。正常发布不得再询问用户粘贴 Token。
- **开发机数据面**只负责向本次 release 的固定前缀上传。每次自动生成全新的随机 uploader key；临时
  Worker 的配置和持久态只保存 key 的 SHA-256；原值只在开发机权限收敛文件中落盘，传输期间仅存在于
  TLS 保护的 HTTPS 请求和两端进程内存，不写日志或持久化。完整 inventory 核验成功后上传器强制销毁
  原文件；此前失败则保留同一文件供断点续传，不能中途生成另一把 key。

控制面使用 `scripts/refresh_cloudflare_mcp_oauth.py` 完成免人工刷新。它通过 macOS Security.framework
原生 API 精确读取并原位更新 Generic Password，不调用 `security` 或其他携带 secret 的子进程。默认
service 是 `Codex MCP Credentials`，默认 account 是 `cloudflare|2e40c71145c8b601`；两者只是非敏感的
Keychain locator，可以用同名 CLI 参数 `--service` / `--account` 覆盖。helper 刻意不枚举同一 service 下
的其他条目，避免为“自动发现”读取无关 secret。若 locator 改变，应明确传入唯一 account，而不是扫描或猜测。

helper 从 Keychain JSON 的 `issuer`、`client_id` 和 `token_response.refresh_token` 构造标准
`refresh_token` grant；先通过 RFC 8414 发现同源 HTTPS `token_endpoint`，所有请求都显式经过
`http://agent.baidu.com:8891`，禁止重定向并设置连接/读取超时。刷新成功后保留 JSON 中未知字段，原位更新
`access_token`、`expires_in`、`expires_at`，并仅在响应提供新 `refresh_token` 时执行 rotation；13 位 Unix
毫秒等原有 expiration 编码保持不变。stdout/stderr 只有非敏感状态码、刷新动作与规范化到期时间；即使
expiration 对象带有未知字段，也不会把这些字段带出 Keychain。

刷新前 helper 会取得当前用户专属的跨进程 advisory lock。默认空锁文件位于
`~/Library/Caches/KWBenchLibrary/credential-locks/cloudflare-mcp-oauth.lock`；父目录必须是当前 uid 拥有的
精确 `0700` 非 Git 目录，文件必须是当前 uid 拥有、精确 `0600`、空内容、普通单硬链接且不能是 symlink。
锁覆盖 Keychain read → OAuth discovery/refresh → 同一 Keychain item 原位更新的完整周期。可用非敏感
`--lock-file` 覆盖，但其父目录必须预先满足相同条件；锁文件以非阻塞模式打开，锁歧义或已被其他进程持有时
fail closed。运行期间及日常清理中不得删除或替换这个持久锁 inode。

首次 OAuth 浏览器授权仍由用户亲自完成；此后标准刷新不再询问或接收 Token。若 Keychain 条目不存在、结构
不兼容、权限不足或网络失败，应在创建任何写入口前 fail closed，不能退回永久 API Token。当前固定 Wrangler
的首次 Keychain 初始化路径会把本地加密材料放入子进程 argv，因此仍不得用于这条自动刷新链路。未来若迁移
到 Linux，只能接入 Secret Service、kernel keyring 或同等用户态最小权限 provider，并通过受限 fd/Unix
socket 获取短时 credential；不得把 refresh/access token 放入环境变量、普通文件或进程参数。

## 标准发布流程

在启动或重载执行 Cloudflare MCP 操作的控制面 Agent 前，先做只读状态检查，再执行按需提前刷新。默认提前
窗口为 900 秒；token 足够新鲜时第二条命令不会发起任何网络请求或写 Keychain：

```bash
python3 scripts/refresh_cloudflare_mcp_oauth.py --dry-status
python3 scripts/refresh_cloudflare_mcp_oauth.py \
  --refresh-window-seconds 900
```

两条命令都不接受 credential 参数，也不读取 credential 环境变量。第一条不访问网络、不更新 Keychain；
第二条只在窗口内刷新。完成后再启动或重载 Cloudflare MCP，使控制面进程读取已刷新的 Keychain 条目。

以下命令应在开发机的干净 GitHub 工作区执行。变量名仅作示例，应为每次发布设置具体值：

```bash
KWBL_SOURCE_RELEASE="/mnt/data/projects/bench-monitor/releases/<immutable-release>"
KWBL_PUBLIC_RELEASE_ID="<yyyyMMddTHHmmssZ-public-vN>"
KWBL_PUBLIC_RELEASE="/mnt/data/projects/bench-monitor/public-releases/$KWBL_PUBLIC_RELEASE_ID"
KWBL_INTERNAL_UI="/mnt/data/projects/bench-monitor/current"
KWBL_UPLOAD_ENDPOINT="https://<temporary-uploader-host>"
KWBL_UPLOAD_CREDENTIAL_DIR="/mnt/data/projects/.kw-bench-library-upload-credentials"
KWBL_UPLOAD_TOKEN_FILE="$KWBL_UPLOAD_CREDENTIAL_DIR/$KWBL_PUBLIC_RELEASE_ID.key"
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

# 先只读规划；不会创建 output-root。将这里输出的两个 root index SHA-256
# 写入/核对 policy pin 后，再用最终 policy 只执行一次正式构建。
python3 scripts/build_public_composite_source.py \
  --base-root "$KWBL_CANONICAL_SOURCE" \
  --overlay-root "$KWBL_PREVIOUS_PUBLIC_RELEASE" \
  --overlay-inventory "$KWBL_PREVIOUS_R2_INVENTORY" \
  --policy config/publication_policy.json \
  --output-root "$KWBL_COMPOSITE_SOURCE" \
  --plan

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
和 `assets/verifiers/` 文件。`data/**`、`site/**`、旧 `assets/index_shards/**`、旧 root index
以及其他 asset namespace 都不会从旧版继承。当前 base 已有的文件永不覆盖；同路径异字节时保留
base，并将双方实际 size/SHA-256 与 `base_retained` 决策写入 provenance。

如果补入的是 mirror 或 preview，builder 只从上一版两个**已经列入 public manifest、且由完整 R2
inventory 复验、同时本地字节也与 manifest 匹配**的 root index 中恢复记录绑定。普通记录的
`bench_id` 必须位于当前 policy `full`，`task_id` 必须存在于当前 immutable release 的对应
`data/benches/<bench>.json`，且 `task_ids` 必须精确等于 `[task_id]`。唯一的非任务例外是 GDPval
仓库级官方资产：ID 必须匹配 `gdpval:asset-<16位小写十六进制>`，role 只能是 `catalog` 或
`reference`；这些记录在 provenance 中与任务记录分开计数并逐项列出 identity，不能伪装成任务绑定。

恢复记录的每一个 deploy/view/preview/page/text 本地路径都必须属于本次已核验 supplement；每个
新增 mirror/preview 文件也必须反向被恢复记录覆盖。只要记录混入非闭包路径、与 base 已有路径冲突、
存在未知任务或未绑定补充文件，构建立即失败。内部 `object_path` 不进入恢复后的公网记录。
builder 保留 base 的现有记录与 hashed shards，只把合格记录以稳定顺序加入复制出的 root index，
随后确定性重算 summary；preview index 绑定新生成 mirror index 的 SHA-256。生成 index 的 size、
SHA-256、记录集合哈希、supplement 路径集合哈希、任务/仓库级记录数和例外 ID 均进入 provenance。

输出必须是全新、非 `current`、非 `live`、非 `releases` 的目录。完成标记和每个补入对象的
path/size/SHA-256/transfer、两份 manifest 哈希、R2 inventory 哈希与摘要、策略哈希、跳过与冲突
统计以及 root index 恢复审计均写入 composite 根目录的 `.kwbl-composite-provenance.json`
（`0644`）；该顶层文件不进入
公网引用闭包。composite 只是一次公网导出的开发机审计源，不替代 canonical immutable release，
也不能反向覆盖开发机 `current`。

正式规划和构建前，builder 会对 canonical base `release_manifest.json` 中的**每一个 payload**
逐项重新核验 regular-file、size 和 SHA-256，并反向遍历 base 文件树。除固定位置且不自列入 payload
的 `release_manifest.json` 外，任何未登记文件（包括意外 provenance、临时文件或工具输出）都会失败，
从而保证后续 `copytree` 不可能把 manifest 外字节带进 composite。若确需以既有 composite 作为新 base，
必须先生成新的 canonical immutable release 和完整 manifest，不能给顶层 provenance 开通隐式例外。

记录先递归剥离唯一明确不公开的 `object_path`，再依次复用 `export_public_release.py` 的
`sanitize_json`、递归发现与 normalize 语义，与正式导出的处理顺序完全一致。Office 临时锁文件会在
路径发现前排除，敏感字段和内部路径会先脱敏；写入 composite 的恢复记录本身也是这一安全版本。
路径发现支持嵌套 dict/list、chunks、`/bench-monitor/`、`bench-monitor/`、`./`、leading `/` 和 URL
decode。strict reference key、任何 `*_url`，以及 base/overlay
中实际存在的路径都必须落在本次 verified supplement 内；跨 Benchmark 路径一律失败。只有 exporter
本来也会忽略的“non-strict key + 两侧磁盘均不存在”说明性/溯源字符串不计入闭包，其数量和稳定路径
集合哈希会单独写入 provenance，避免把 `logical_path` 等说明字段误当成已发布文件。

构建完成后，将本次命令的 `--source` 指向 `$KWBL_COMPOSITE_SOURCE`，重新运行原版 exporter 的
`--validate-only` 与 `--validate-closure`。两项必须都通过；若当前 root index 指向缺失的 base
hashed index shard，或仍有任何未被严格允许的缺口，应继续 fail closed，不能从旧版偷补。最终公开候选
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

标准入口不接收人工输入的 uploader key。先创建一个仅当前开发机用户可写的独立目录，再由生成器用
`O_EXCL | O_NOFOLLOW` 创建 64 字节、无换行、权限精确为 `0600` 的随机 key。命令唯一的 stdout 是
`path`、`bytes` 和 `sha256` JSON，不包含原值；将其中 `sha256` 配置为临时 Worker 的
`UPLOAD_KEY_SHA256`：

```bash
install -d -m 0700 "$KWBL_UPLOAD_CREDENTIAL_DIR"
python3 scripts/create_one_time_upload_key.py \
  --output "$KWBL_UPLOAD_TOKEN_FILE"
```

凭据目录必须独立于 Git；生成器与读取器都会逐层检查实际父目录中的 `.git` marker 和常规裸仓库结构并
硬性拒绝，也会拒绝带 `GIT_DIR` 或 `GIT_WORK_TREE` 外部 Git 上下文的进程，不能依赖 `.gitignore`。因此，
标准 worktree/裸仓库中的手工 key 也不能用于上传。Git 允许在完全不标记工作树目录的另一处元数据仓库中
配置 `core.worktree`；单靠一个输出路径无法穷举全盘并证明这种非生效外部配置不存在，所以标准流程还固定
使用专用凭据根目录，禁止把它配置成任何仓库的外部 worktree。生成器同时拒绝覆盖既有路径。重试同一个
release 时必须复用该
文件；只有新 release 才创建新路径。上传器通过
保留的父目录 fd，以 `O_NOFOLLOW | O_NONBLOCK` 读取文件，并要求它是当前 uid 拥有、单硬链接、权限不宽于
`0600` 的普通文件。仅为兼容旧文件，读取器会规范化首尾空白；新生成器始终写入无空白的精确值。Cloudflare
配置和发布记录中只允许出现规范化后 key 的 SHA-256，不能出现原始 key。

若临时端点复用生产域名，只挂载精确的 HTTPS path route
`https://benchlibrary.com/_kwbl-upload/*`；不要创建无 scheme、全站或通配子域路由。上传前先验证无密钥访问返回 404、带密钥 health 返回精确新旧 prefix；清理时先删除这条 route，再删除临时 Worker。
客户端的 `--endpoint` 只接受不含 userinfo、path、query 或 fragment 的 HTTPS origin；所有请求禁用重定向，
任何 30x（包括跨域或降级到 HTTP）都会在发送后续请求前失败，避免自定义认证头泄露。

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
  --workers 12
```

若 Cloudflare 内部复用在真实环境中持续失败，保持同一个新 release 与断点文件，去掉 `--copy-source-manifest` 后重跑即可全量直传；不要放宽 prefix、路径、SHA 或 inventory 校验来换取复用成功。

上传器支持断点续传，并在结束时抓取完整 R2 inventory。它会一直持有最初打开的 key inode；只有完整
inventory 一一对应核验成功后，才重新核对父目录中的 dev/inode 并强制删除同一个文件。旧命令行中的
`--delete-token-on-success` 仍可解析以兼容既有自动化，但现在是无须传入的同义参数，不存在保留 key 的
成功路径。分页、上传或 inventory 核验失败时 key 保留，以便同一 release 安全续传。

若 key 的 `unlink` 已成功（包括同一 inode 已被另一个受信进程移除）、但随后父目录 `fsync` 失败，上传器会
把所有可捕获的异常与进程内取消信号转换为可判定的
`UploadCredentialRetirementFailure`：`inventory_verified=True`、`token_file_unlinked=True`、
`parent_fsync_completed=False`、`retry_upload=False`。这不属于“上传失败并保留 key”的情形：当前目录项已
移除，但崩溃后的删除持久性无法证明。CLI 会以专用退出码 `3` 返回，并在 stderr 输出不含 secret 的同字段
JSON，监督进程必须按 `retry_upload=False` 分流，不得把所有非零退出码统一重跑。此时应立即撤销临时
route 和 Worker，确认凭据路径不存在并记录该状态，不得重建同路径 key。临时写入口清理完成后，已经通过
的 R2 inventory 仍可作为后续发布判断依据。

若中断恰好发生在 `unlink` 系统调用已经生效、但调用方尚未记录结果的窗口，上传器会通过保留的 inode 和
父目录 fd 对账并再次 `fsync`。对账确认原 key 已无硬链接时同样返回专用退出码 `3` 和
`retry_upload=False`；补充同步成功则报告 `parent_fsync_completed=True` 及
`code=upload_token_unlinked_after_interruption`，补充同步失败则使用上述 `False` 状态。两者都不得重试上传。

若 inode/path 身份复核等其他退休步骤失败，状态为 `token_file_unlinked=False`、
`parent_fsync_completed=null`、`code=upload_token_retirement_failed`。此时 inventory 已验证，仍不得重传；先撤销
临时 route 和 Worker，再按保留 fd 所记录的 inode 与实际路径人工排查并销毁残余 key。

`SIGKILL`、主机掉电或内核崩溃无法由进程转换成上述结构化状态。因此监督进程也不得把“无结构化状态的未知
退出”自动视为可重试：应先确认临时写入口、凭据路径与已验证 inventory 的实际状态，再由控制面恢复或清理。

切换前必须再做一次离线一一对应核验，包括 key、size、SHA-256 custom metadata 及 Content-Type、Cache-Control、Content-Encoding、Content-Disposition HTTP metadata：

```bash
python3 scripts/verify_r2_release.py \
  --manifest "$KWBL_PUBLIC_RELEASE/data/public_manifest.json" \
  --inventory "/mnt/data/projects/bench-monitor/public-releases/.$KWBL_PUBLIC_RELEASE_ID.r2-inventory.json"
```

只有当对象 key 集合、文件数、总字节数、逐文件大小和 SHA-256 metadata 全部精确一致时，才能继续。上传成功后立即删除临时上传 Worker、临时域名和残余密钥文件；生产环境不保留写入口。

## Worker 切换、验收与回滚

先记录线上旧的 `PUBLIC_RELEASE_ID`、当前 deployment id 和其 100% 流量对应的 Worker
version id。后者是包含旧代码、静态资源、bindings 与旧 release 指针的精确回滚锚点；不要只记
release id。再通过已认证控制面的 Cloudflare Version Upload API 创建新 version，上传经过本地 SHA-256
核验的 `src/index.js` module，并显式提交且只提交以下两个 bindings：

- `PUBLIC_CORPUS`：R2 bucket `benchlibrary-public`；
- `PUBLIC_RELEASE_ID`：已通过 inventory 核验的新 release id。

创建后必须回读 version settings，确认 compatibility date/flags、module SHA-256 和上述 exact-2-binding 均
符合预期，再通过 Deployment API 把该 version 切到 100%。生产环境禁止执行 `npm run deploy` 或
`wrangler deploy`；仓库现有 Wrangler 入口仅供非生产环境使用，其 `STATIC_ASSETS` 与 custom domain 配置
不属于当前公网生产架构。

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

## 已验证数据版本上的 UI 增量发布（2026-09-29）

仅涉及展示页面、导航和独立活动素材，且不改变 corpus、策略或 BenchList 数据时，允许使用
[活动专区的精确路径增量流程](ACTIVITIES.md#ui-增量发布)。此流程扩展上文的单 release 模型：
保留已完整验证的 `PUBLIC_RELEASE_ID`，在版本化 Worker module 中固定增量 release、base release
和逐对象清单。生产仍恰好两个 bindings；新增对象不覆盖历史内容。

只需上传并完整验证增量集合，不复制或重新上传原有 20 GB 语料。发布记录必须同时记载数据 release、
增量 release、两个模块的哈希、全部增量对象的校验结果，以及前一 Worker version 作为回滚点。
普通题库/策略变更仍走完整导出与 inventory 流程，不适用此例外。
