# BenchList 公开版维护

## 构建

从经过核验的内部快照生成 UI 和公开数据，不能直接复制内部审计 JSON 或 Markdown：

```bash
python3 scripts/build_public_ui.py --source "$KWBL_INTERNAL_UI" --output site
python3 scripts/build_public_benchlist.py --source "$KWBL_INTERNAL_UI" --output site
node --test test/*.test.mjs
python3 -m unittest discover -s tests
```

第二个构建器采用字段白名单：只保留已核实的发布正文/附录声明、模型发布日期依据、
Benchmark 的修订说明及第一方来源。内部 sourceDocument、原文描述/型号/优先级、
原表行号、原文 snapshot 下载、未核实声明均不进入公开数据。每份截图必须被保留的声明引用，
并与内部审计 inventory 的 SHA-256 一致。

`site/benchlist.json` 和 `site/benchlist-audit.md` 是公开产物；38 份公开截图位于
`site/benchlist-evidence/`。发布后 URL 为 `/benchlist.json`、`/benchlist-audit.md` 和
`/benchlist-evidence/*`，由 Worker 映射到同一 R2 release 的 `site/` 命名空间。
这些文件与题库共享发布指针，不需要开放额外接口或更改 Worker bindings。

## 统计契约

- 快照日期 2026-09-14，六个月窗口为 2026-03-14 至 2026-09-14（含两端）。
- 127 项 Benchmark、111 条登记型号、88 个窗口内统计模型、990 个有效引用组合。
- GPT-5.6 变体在全期归并，GPT-6 独立；同一变体按自身发布日期进入月份。
- 月分母依次为 7、25、7、14、11、16、9，总和不要求等于全期去重分母。
- HLE 全期 39/88，月引用数 4、15、2、5、4、7、2。
- 截图、文字报告和 API 模块都展示来源；空白不代表未参评，引用频次不代表性能得分。
- 公开版不提供“内部原文提及”统计模式，也不显示内部优先级。

已有日期/归并/趋势测试已移入 `test/benchlist_*.test.mjs`，直接使用公开产物回归。
`tests/test_build_public_benchlist.py` 验证公开字段边界、负例和截图哈希。

## 发布和验收

遵循 [发布手册](RELEASE_RUNBOOK.md) 完成源码版本、公开 exporter、R2 inventory、
exact-2-binding Worker version、100% 切流和匿名 smoke。仅提交 GitHub 不代表公网已更新。
不要使用生产 Wrangler deploy，不要原地覆盖旧 release。

题库数据未变化的 UI 发布，可以继续使用先前已经审计的 corpus/composite 源；先核对新旧内部
release manifest，确认题库 data/assets 的路径、size、SHA-256 完全一致，差异仅限本次 UI 和
BenchList 文件。仍须重新运行 exporter 的 validate-only、validate-closure 和完整导出，
新 UI 与公开数据由当前内部版本生成。记录 corpus 源与 BenchList/UI 源，不能将两者混写成一个版本。

浏览器验收包括直达 `#view=benchlist`、缺少本地题库时独立加载、模型列分页、覆盖率、
全屏趋势、月份证据、截图以及回到题库。上线后核对公开 JSON/JS/CSS/截图与发布 manifest 的哈希。
内部版本保留内部审计功能，公开版和内部版的已核实引用统计必须一致。
