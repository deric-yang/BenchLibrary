# 活动专区

入口为 `/activities/`，第一项为 VibeMotionBench 六屏路演；首页导航在 BenchList 后提供“活动专区”。
活动页保留三个模块入口，用同源 iframe 隔离路演的样式和滚动。视频按点击加载，支持全屏及 HTTP Range。

## 来源与维护

2026-09-29 经项目维护者指定并授权公开的路演页面及配套素材快照。共 5 段 MP4、10 张 JPEG。
页面内容与素材的权利归原作者及各自权利人；仓库的软件许可证不改变素材的许可范围。
此页面展示原始提案的观点和当时记录，不代表本站重新核验了其中的产品版本、日期或统计数字。

迁移时保留六屏内容与视觉结构，移除 Google Fonts 远程依赖（使用系统字体回退），
将脚本移至 `presentation.js` 以兼容现有 CSP，并修复减少动态效果模式下的动画循环及播放失败状态。
全部运行资源来自本站；不代理内网服务，也不依赖内网 API。服务器端源码并非本次迁移的必要条件。

编辑 `site/activities/` 后，更新 `config/activity_release.json` 的新 release ID，并执行
`node scripts/build_site_overlay.mjs`。每次发布使用新的不可变前缀，不覆盖既有 release。
首页生成器也保留活动入口，因此以后重建公开 UI 不会丢失该入口。

## UI 增量发布

活动模块不改变题库数据。Worker 的 `src/site-overlay.js` 是从人工审阅的路径清单生成的模块：

- 只在 `PUBLIC_RELEASE_ID` 与清单的 `base_release` 完全一致时启用。
- 只有逐条列出的 `site/` 文件从新 release 读取，没有目录通配或旧对象回退。
- 每个对象的长度和 SHA-256 元数据须匹配，否则返回 503；不存在则返回 404。
- `/data/`、`/assets/`、BenchList 和未列出的 UI 文件继续读取原来经过完整验证的 release。
- 新版本仍只有 `PUBLIC_CORPUS` 与 `PUBLIC_RELEASE_ID` 两个 bindings；通过 Version Upload / Deployment API 发布。
- 回滚只需把 100% 流量切回上一 Worker version，无需删除或覆盖任何对象。

上传新增清单中的所有对象，核对完整增量 inventory 的对象集合、大小、SHA-256 和 HTTP metadata，
读取所有新增线上文件验证真实字节，然后销毁一次性上传密钥并删除临时 route/Worker。
必须回读全部 Worker modules 并与已提交源码逐字节比对，然后才能切换生产流量。

以后发布完整 corpus 时，将本模块合入完整的 `site/` 导出并移除或更新 overlay；
不得只更改 base_release 以套用未重新核验的增量清单。旧数据与增量对象均须保留供回滚。
