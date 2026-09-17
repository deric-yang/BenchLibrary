"use strict";

(() => {
    const OWN_KINDS = new Set(["release_main", "release_appendix"]);
    const STATUS = {
        confirmed: "已核实", corrected: "需纠正", unverified: "待核实",
        not_found: "未找到证据", ambiguous: "口径不明确",
        qualified: "需补限定",
    };
    const KIND = {
        release_main: "发布正文 / 报告正文", release_appendix: "报告附录",
        third_party: "第三方评测", comparison_only: "仅被比较", unknown: "来源类型待核实",
    };
    const PROVIDERS = [
        "OpenAI", "Anthropic", "Google", "DeepSeek", "Alibaba", "Moonshot", "Z.ai",
        "xAI", "Meta", "Microsoft", "Baidu", "Tencent", "ByteDance", "MiniMax", "Xiaomi", "Other",
    ];
    const CATEGORY_ORDER = ["Knowledge Work", "Coding", "Multimodal", "Reasoning"];
    const CATEGORY_LABEL = {
        "Knowledge Work": "知识工作", Coding: "编程", Multimodal: "多模态", Reasoning: "推理",
    };
    const STORE_KEY = "kw-benchlist-shortlist-v1";
    const MODEL_PAGE_SIZE = 40;
    const state = {
        data: null, loading: null, active: false, category: "all", query: "", priority: "all",
        projection: "provider", mode: "verified", selectedOnly: false, additionsOnly: false, selected: new Set(),
        page: 0, pageFilterKey: "",
        drawer: null, opener: null, storageAvailable: true,
    };
    const refs = {};
    let auditCache = null;

    // A synchronous render shares derived values; no cache survives a data or view update.
    function withAuditCache(data, callback) {
        if (auditCache?.data === data) {
            return callback();
        }
        const previous = auditCache;
        auditCache = {data, maps: new Map()};
        try {
            return callback();
        }
        finally {
            auditCache = previous;
        }
    }

    function memoValue(group, key, compute, data = state.data) {
        if (!auditCache || auditCache.data !== data) {
            return compute();
        }
        if (!auditCache.maps.has(group)) {
            auditCache.maps.set(group, new Map());
        }
        const cache = auditCache.maps.get(group);
        if (!cache.has(key)) {
            cache.set(key, compute());
        }
        return cache.get(key);
    }

    function string(value) {
        if (typeof value === "string") {
            return value;
        }
        if (Array.isArray(value)) {
            return value.map(string).filter(Boolean).join("；");
        }
        return value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value);
    }

    function modelName(value) {
        return typeof value === "object" && value ? string(value.model || value.name || value.id) : string(value);
    }

    function releaseKey(value) {
        const name = modelName(value);
        return memoValue("releaseKeys", name,
            () => name.normalize("NFKC").toLowerCase().replace(/[\s_–—]+/g, "-").trim(), auditCache?.data);
    }

    function providerFor(model, explicit = "") {
        const value = `${explicit} ${model}`.toLowerCase();
        const rules = [
            [/openai|gpt|\bo[134](?:\b|-)/, "OpenAI"], [/anthropic|claude|opus|sonnet|haiku/, "Anthropic"],
            [/google|gemini|gemma/, "Google"], [/deepseek/, "DeepSeek"], [/alibaba|qwen|通义/, "Alibaba"],
            [/moonshot|kimi|月之暗面/, "Moonshot"], [/z\.ai|zhipu|glm|智谱/, "Z.ai"], [/xai|x\.ai|grok/, "xAI"],
            [/meta|llama/, "Meta"], [/microsoft|\bphi\b/, "Microsoft"], [/baidu|ernie|文心/, "Baidu"],
            [/tencent|hunyuan|混元/, "Tencent"], [/bytedance|doubao|seed|豆包/, "ByteDance"],
            [/minimax/, "MiniMax"], [/xiaomi|mimo/, "Xiaomi"],
        ];
        return rules.find(([pattern]) => pattern.test(value))?.[1] || string(explicit) || "Other";
    }

    function originals(row) {
        const raw = row.originalModels;
        const values = Array.isArray(raw) ? raw : string(raw).split(/[,，;；\n]+/);
        return [...new Map(values.map(modelName).filter(Boolean).map((name) => [releaseKey(name), name])).values()];
    }

    function reviews(row) {
        return [...(Array.isArray(row.claimReviews) ? row.claimReviews : []),
            ...(Array.isArray(row.additionalCitations) ? row.additionalCitations : [])]
            .filter((claim) => claim && modelName(claim.model));
    }

    function validDate(value) {
        if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) {
            return false;
        }
        const parsed = new Date(`${value}T00:00:00Z`);
        return !Number.isNaN(parsed.valueOf()) && parsed.toISOString().slice(0, 10) === value;
    }

    function registry(data = state.data) {
        return Array.isArray(data?.modelRegistry) ? data.modelRegistry : [];
    }

    function registryMatch(model, canonical = false, data = state.data) {
        const key = releaseKey(model);
        const nameFor = (item) => canonical ? item.countingModel || item.model : item.model;
        if (!auditCache || auditCache.data !== data) {
            return registry(data).find((item) => releaseKey(nameFor(item)) === key);
        }
        const index = memoValue("registryIndexes", canonical, () => {
            const entries = new Map();
            for (const item of registry(data)) {
                const itemKey = releaseKey(nameFor(item));
                if (!entries.has(itemKey)) {
                    entries.set(itemKey, item);
                }
            }
            return entries;
        }, data);
        return index.get(key);
    }

    function releaseBounds(release) {
        if (validDate(release?.releaseDate)) {
            return {start: release.releaseDate, end: release.releaseDate, isRange: false};
        }
        const range = release?.releaseDateRange;
        return validDate(range?.start) && validDate(range?.end) && range.start <= range.end
            ? {start: range.start, end: range.end, isRange: true} : null;
    }

    function releaseDateLabel(release) {
        const dates = releaseBounds(release);
        if (!dates) {
            return "未核实";
        }
        if (!dates.isRange || dates.start === dates.end) {
            return dates.start;
        }
        const nextDay = new Date(`${dates.end}T00:00:00Z`);
        nextDay.setUTCDate(nextDay.getUTCDate() + 1);
        if (dates.start.endsWith("-01") && dates.start.slice(0, 7) === dates.end.slice(0, 7)
            && nextDay.getUTCDate() === 1) {
            return `${dates.start.slice(0, 7)}（月内，具体日期未公布）`;
        }
        return `${dates.start} — ${dates.end}（日期范围）`;
    }

    function releaseScope(release, data = state.data) {
        return memoValue("releaseScopes", release, () => computeReleaseScope(release, data), data);
    }

    function computeReleaseScope(release, data) {
        const scope = data?.modelScope;
        const dates = releaseBounds(release);
        if (!dates) {
            return {eligible: false, reason: string(release.exclusionReason) || "发布日期未核实，暂不计数"};
        }
        if (dates.isRange && !(Array.isArray(release.dateSources) && release.dateSources.some((source) =>
            safeUrl(typeof source === "string" ? source : source?.url || source?.sourceUrl)))) {
            return {eligible: false, reason: "发布日期范围缺少可核验的官方来源，暂不计数"};
        }
        if (!validDate(scope?.startDate) || !validDate(scope?.endDate) || scope.startDate > scope.endDate) {
            return {eligible: false, reason: "发布统计窗口未配置，暂不计数"};
        }
        if (dates.start < scope.startDate || dates.end > scope.endDate) {
            return {eligible: false, reason: string(release.exclusionReason)
                || (dates.isRange ? "发布日期范围未完整落在本轮六个月窗口内" : "发布日期在本轮六个月窗口外")};
        }
        return release.eligible === true ? {eligible: true, reason: ""}
            : {eligible: false, reason: string(release.exclusionReason) || "发布范围尚未核实，暂不计数"};
    }

    function claimScope(claim, data = state.data) {
        return memoValue("claimScopes", claim, () => computeClaimScope(claim, data), data);
    }

    function computeClaimScope(claim, data) {
        const record = registryMatch(claim.model, false, data);
        const countingModel = modelName(record?.countingModel || claim.countingModel || claim.model);
        const releaseDate = record ? record.releaseDate : claim.releaseDate;
        const releaseDateRange = record ? record.releaseDateRange : claim.releaseDateRange;
        const provider = record?.provider || claim.provider;
        const scope = releaseScope(record || {...claim, eligible: claim.inScope === true}, data);
        let reason = scope.reason;
        if (Array.isArray(data?.modelRegistry) && !record) {
            reason = "发布清单尚无此实际型号，暂不计数";
        }
        else if (claim.inScope !== true && scope.eligible) {
            reason = string(claim.exclusionReason) || "该引用的发布范围尚未核实，暂不计数";
        }
        return {countingModel, releaseDate, releaseDateRange, provider, record,
            eligible: scope.eligible && claim.inScope === true && !reason, reason};
    }

    function inScope(claim, data = state.data) {
        return claimScope(claim, data).eligible;
    }

    function countingName(claim, data = state.data) {
        return claimScope(claim, data).countingModel;
    }

    function isOwnConfirmed(claim, data = state.data) {
        return claim.status === "confirmed" && OWN_KINDS.has(claim.kind)
            && Boolean(safeUrl(claim.sourceUrl)) && inScope(claim, data);
    }

    function uniqueConfirmed(row, data = state.data) {
        return memoValue("confirmedRows", row, () => computeUniqueConfirmed(row, data), data);
    }

    function computeUniqueConfirmed(row, data) {
        const unique = new Map();
        for (const claim of reviews(row).filter((item) => isOwnConfirmed(item, data))) {
            const info = claimScope(claim, data);
            const key = releaseKey(info.countingModel);
            if (!unique.has(key)) {
                unique.set(key, {...claim, model: modelName(claim.model),
                    countingModel: info.countingModel, provider: info.provider});
            }
        }
        return [...unique.values()];
    }

    function rowOriginals(row, data = state.data) {
        return memoValue("originalRows", row, () => computeRowOriginals(row, data), data);
    }

    function computeRowOriginals(row, data) {
        const originalsToReview = Array.isArray(row.claimReviews) ? row.claimReviews : [];
        const claims = originalsToReview.filter((claim) => inScope(claim, data));
        const eligible = new Set(originalsToReview.length
            ? claims.map((claim) => releaseKey(countingName(claim, data)))
            : registry(data).filter((item) => releaseScope(item, data).eligible)
                .map((item) => releaseKey(item.countingModel || item.model)));
        const models = Array.isArray(row.originalClaimModels) ? row.originalClaimModels.map(modelName)
            : claims.map((claim) => countingName(claim, data));
        return [...new Map(models
            .filter((name) => name && eligible.has(releaseKey(name))).map((name) => [releaseKey(name), name])).values()];
    }

    function filterAdditions(rows, onlyAdditions) {
        return onlyAdditions ? rows.filter((row) => row.isAddition === true) : rows;
    }

    function columnFor(model, provider, projection) {
        return projection === "model" ? releaseKey(model) : providerFor(model, provider);
    }

    function cellSummary(row, column, projection = "provider", data = state.data) {
        if (auditCache?.data === data) {
            const cells = memoValue(`cells:${projection}`, row, () => {
                const entries = new Map();
                const cellFor = (key) => {
                    if (!entries.has(key)) {
                        entries.set(key, {confirmed: [], originals: [], unresolved: []});
                    }
                    return entries.get(key);
                };
                const confirmed = uniqueConfirmed(row, data);
                const confirmedKeys = new Set(confirmed.map((claim) => releaseKey(claim.countingModel)));
                for (const claim of confirmed) {
                    cellFor(columnFor(claim.countingModel, claim.provider, projection)).confirmed.push(claim);
                }
                for (const name of rowOriginals(row, data)) {
                    const match = registryMatch(name, true, data);
                    const cell = cellFor(columnFor(name, match?.provider, projection));
                    cell.originals.push(name);
                    if (!confirmedKeys.has(releaseKey(name))) {
                        cell.unresolved.push(name);
                    }
                }
                return entries;
            }, data);
            return cells.get(column) || {confirmed: [], originals: [], unresolved: []};
        }
        const confirmed = uniqueConfirmed(row, data).filter((claim) =>
            columnFor(claim.countingModel, claim.provider, projection) === column);
        const names = rowOriginals(row, data).filter((name) => {
            const match = registryMatch(name, true, data);
            return columnFor(name, match?.provider, projection) === column;
        });
        const confirmedKeys = new Set(uniqueConfirmed(row, data).map((claim) => releaseKey(claim.countingModel)));
        const unresolved = names.filter((name) => !confirmedKeys.has(releaseKey(name)));
        return {confirmed, originals: names, unresolved};
    }

    function categoryFor(value) {
        const raw = string(value).trim();
        if (/knowledge|work|知识|办公|agentic|agent tasks/i.test(raw)) {
            return "Knowledge Work";
        }
        if (/coding|code|编程|软件/i.test(raw)) {
            return "Coding";
        }
        if (/multimodal|多模态|视觉|vision|video|audio/i.test(raw)) {
            return "Multimodal";
        }
        if (/reason|推理|数学|math|science|科学/i.test(raw)) {
            return "Reasoning";
        }
        return raw || "其他";
    }

    function normalizeData(payload) {
        if (!payload || !Array.isArray(payload.benchmarks)) {
            throw new Error("审计数据缺少 benchmarks 列表。");
        }
        const seen = new Set();
        const benchmarks = payload.benchmarks.map((row, index) => {
            const id = string(row.id || `benchlist-${index + 1}`);
            if (seen.has(id)) {
                throw new Error(`审计数据有重复条目：${id}`);
            }
            seen.add(id);
            return {...row, id, name: string(row.name || id), category: categoryFor(row.category),
                priority: string(row.priority || "待定").toUpperCase()};
        });
        return {...payload, benchmarks};
    }

    function safeUrl(value, localOnly = false) {
        if (typeof value !== "string" || !value.trim()) {
            return "";
        }
        try {
            const url = new URL(value, document.baseURI);
            if (!["http:", "https:"].includes(url.protocol) || url.username || url.password) {
                return "";
            }
            if (localOnly && url.origin !== new URL(document.baseURI).origin) {
                return "";
            }
            if (globalThis.KW_BENCH_PUBLIC_MODE === true && /(?:baidu-int\.com|^10\.)/.test(url.hostname)) {
                return "";
            }
            return url.href;
        }
        catch (_error) {
            return "";
        }
    }

    function el(tag, className, text) {
        const node = document.createElement(tag);
        if (className) {
            node.className = className;
        }
        if (text !== undefined) {
            node.textContent = string(text);
        }
        return node;
    }

    function button(text, className, action) {
        const node = el("button", className, text);
        node.type = "button";
        if (action) {
            node.addEventListener("click", action);
        }
        return node;
    }

    function link(text, url, className = "bl-source-link", localOnly = false) {
        const href = safeUrl(url, localOnly);
        if (!href) {
            return null;
        }
        const node = el("a", className, text);
        node.href = href;
        node.target = "_blank";
        node.rel = "noopener noreferrer";
        return node;
    }

    function appendLink(parent, text, url, className, localOnly) {
        const node = link(text, url, className, localOnly);
        if (node) {
            parent.append(node);
        }
    }

    function readSelection() {
        try {
            const saved = JSON.parse(localStorage.getItem(STORE_KEY) || "[]");
            state.selected = new Set(Array.isArray(saved) ? saved.filter((id) => typeof id === "string") : []);
        }
        catch (_error) {
            state.selected = new Set();
            state.storageAvailable = false;
        }
    }

    function persistSelection() {
        try {
            localStorage.setItem(STORE_KEY, JSON.stringify([...state.selected]));
        }
        catch (_error) {
            state.storageAvailable = false;
            refs.selectionStatus.textContent = "浏览器未允许保存；本次选择仍可使用。";
        }
    }

    async function activate() {
        const root = document.getElementById("benchlistWorkspace");
        if (!root) {
            return;
        }
        state.active = true;
        document.body.classList.add("benchlist-active");
        root.classList.remove("hidden");
        document.getElementById("openBenchList")?.setAttribute("aria-current", "page");
        document.getElementById("benchlistCatalogLink")?.removeAttribute("aria-current");
        if (state.data) {
            return;
        }
        if (state.loading) {
            return state.loading;
        }
        root.replaceChildren(el("div", "bl-loading", "正在读取 BenchList 引用审计…"));
        root.setAttribute("aria-busy", "true");
        state.loading = (async () => {
            try {
                const response = await fetch(new URL("benchlist.json", document.baseURI), {
                    credentials: "same-origin", cache: "no-store",
                });
                if (!response.ok) {
                    throw new Error(`审计文件读取失败（HTTP ${response.status}）。`);
                }
                state.data = normalizeData(await response.json());
                readSelection();
                buildWorkspace(root);
                render();
            }
            catch (error) {
                state.data = null;
                const failure = el("div", "bl-empty");
                failure.append(el("h2", "", "BenchList 暂时没有加载成功"), el("p", "", error.message),
                    button("重新读取", "bl-button bl-button-primary", () => void activate()));
                failure.setAttribute("role", "alert");
                root.replaceChildren(failure);
            }
            finally {
                root.removeAttribute("aria-busy");
                state.loading = null;
            }
        })();
        return state.loading;
    }

    function deactivate() {
        state.active = false;
        closeDrawer();
        document.getElementById("benchlistWorkspace")?.classList.add("hidden");
        document.body?.classList.remove("benchlist-active");
        document.getElementById("openBenchList")?.removeAttribute("aria-current");
        document.getElementById("benchlistCatalogLink")?.setAttribute("aria-current", "page");
    }

    function buildWorkspace(root) {
        root.replaceChildren();
        const hero = el("div", "bl-hero");
        const heroCopy = el("div", "bl-hero-copy");
        heroCopy.append(el("p", "bl-eyebrow", "RELEASE EVIDENCE · BENCHMARK WATCHLIST"));
        const title = el("h1", "", "BenchList");
        title.id = "benchlistTitle";
        heroCopy.append(title, el("p", "bl-lead", "哪些评测，真正出现在模型发布里？"),
            el("p", "bl-hero-description", "逐项核对发布引用、修正评测口径，为下一次模型 release 整理有证据的候选清单。"));
        const heroAside = el("div", "bl-hero-aside");
        const checked = string(state.data.checkedAt).slice(0, 10) || "未标注";
        heroAside.append(el("span", "bl-date-label", "本轮证据核查"), el("strong", "bl-date", checked));
        const links = el("div", "bl-document-links");
        if (globalThis.KW_BENCH_PUBLIC_MODE !== true) {
            appendLink(links, "知识库原文 ↗", state.data.sourceDocument?.url);
        }
        appendLink(links, "下载核验稿 ↗", state.data.downloads?.markdown, "bl-source-link", true);
        appendLink(links, "JSON 数据 ↗", state.data.downloads?.json || "data/benchlist.json", "bl-source-link", true);
        links.append(button("模型范围与发布日期", "bl-text-button bl-registry-button", (event) =>
            openModelRegistry(event.currentTarget)));
        heroAside.append(links);
        hero.append(heroCopy, heroAside);
        root.append(hero);
        refs.stats = el("div", "bl-stats");
        root.append(refs.stats);

        const auditNotice = el("div", "bl-audit-notice");
        const scopeCopy = el("p", "");
        scopeCopy.append(el("strong", "", scopeLabel()),
            el("span", "", " · GPT-5.6 Sol / Terra / Luna 合计一个模型，GPT-6 独立。深色表示采用频次，不代表分数或质量；空白不等于未参评。"));
        auditNotice.append(el("span", "bl-notice-mark", "i"), scopeCopy);
        root.append(auditNotice);

        const workspace = el("div", "bl-matrix-card");
        refs.tabs = el("div", "bl-tabs");
        refs.tabs.setAttribute("role", "tablist");
        refs.tabs.setAttribute("aria-label", "能力板块");
        workspace.append(refs.tabs);
        buildControls(workspace);
        refs.legend = el("div", "bl-legend");
        refs.matrixSummary = el("p", "bl-matrix-summary");
        refs.matrixSummary.setAttribute("aria-live", "polite");
        refs.matrixSummaryText = el("span");
        refs.pagination = el("span", "bl-pagination");
        refs.pagination.setAttribute("role", "group");
        refs.pagination.setAttribute("aria-label", "模型矩阵分页");
        refs.previousPage = button("上一页", "bl-text-button", () => changePage(-1));
        refs.previousPage.setAttribute("aria-label", "上一页 Benchmark");
        refs.nextPage = button("下一页", "bl-text-button", () => changePage(1));
        refs.nextPage.setAttribute("aria-label", "下一页 Benchmark");
        refs.paginationStatus = el("span");
        refs.pagination.append(" · ", refs.previousPage, "　", refs.paginationStatus, "　", refs.nextPage);
        refs.matrixSummary.append(refs.matrixSummaryText, refs.pagination);
        const meta = el("div", "bl-matrix-meta");
        meta.append(refs.matrixSummary, refs.legend);
        workspace.append(meta);
        refs.matrix = el("div", "bl-table-scroll");
        refs.matrix.id = "blMatrixPanel";
        refs.matrix.tabIndex = 0;
        refs.matrix.setAttribute("role", "region");
        refs.matrix.setAttribute("aria-label", "Benchmark 与模型引用矩阵，可横向滚动");
        workspace.append(refs.matrix);
        root.append(workspace);

        const lower = el("div", "bl-lower-grid");
        const selection = el("section", "bl-shortlist-card");
        selection.append(el("p", "bl-eyebrow", "YOUR RELEASE SHORTLIST"), el("h2", "", "PR 候选清单"),
            el("p", "bl-muted", "选择每行的 ☆，保留你的讨论清单。选择只保存在当前浏览器。"));
        refs.shortlist = el("div", "bl-shortlist");
        refs.selectionStatus = el("p", "bl-muted bl-selection-status", "");
        refs.selectionStatus.setAttribute("aria-live", "polite");
        const selectionActions = el("div", "bl-shortlist-actions");
        selectionActions.append(button("复制候选清单", "bl-button", copySelection),
            button("清空选择", "bl-button bl-button-quiet", () => {
                state.selected.clear();
                state.selectedOnly = false;
                refs.selectedOnly.checked = false;
                persistSelection();
                render();
            }));
        selection.append(refs.shortlist, selectionActions, refs.selectionStatus);
        const methodology = el("section", "bl-methodology-card");
        methodology.append(el("p", "bl-eyebrow", "HOW TO READ THIS MATRIX"), el("h2", "", "证据口径"));
        const methods = el("ol", "bl-methodology-list");
        const entries = [
            `${scopeLabel()}（含起止日）。窗口外或发布日期未核实的模型保留证据，但不进入矩阵、采用次数与模型筛选。`,
            "只计入已核实、发布方对自己模型的正文或附录采用。按统计模型去重：GPT-5.6 Sol / Terra / Luna 合计一个，GPT-6 独立；同一统计模型的多个网页、截图或分数只计一次。",
            "矩阵列包括发布清单中符合窗口的模型，即使尚无任何引用证据。空白表示本轮未取得可计数证据，不代表未参与评测或从未引用。",
            "模型覆盖率 = 已核实引用该 Benchmark 的统计模型数 / 窗口内全部统计模型数，分母不随板块或矩阵列变化。趋势图按实际型号发布月归组，每月合并变体；仅比较完整月份的数量差或覆盖率百分点差。",
            "原文提及、第三方跑分和报告中的对照模型分别记录；不自动视为该模型自己发布时采用。",
            "候选清单由你选择。引用频次只是选型依据之一，还需结合能力定位、评测成本与可复现性。",
            ...(Array.isArray(state.data.methodology) ? state.data.methodology.map(string) : []),
        ];
        [...new Set(entries)].forEach((entry) => methods.append(el("li", "", entry)));
        methodology.append(methods);
        if (state.data.sourceDocument?.snapshotDate) {
            methodology.append(el("p", "bl-muted", `原文快照：${string(state.data.sourceDocument.snapshotDate)}`));
        }
        lower.append(selection, methodology);
        root.append(lower);
    }

    function buildControls(parent) {
        const controls = el("div", "bl-controls");
        const search = el("label", "bl-search");
        search.append(el("span", "visually-hidden", "搜索 Benchmark、模型与审计内容"));
        const input = el("input");
        refs.search = input;
        input.type = "search";
        input.placeholder = "搜索 Benchmark、模型、关键词…";
        input.setAttribute("aria-label", "搜索 Benchmark、模型与审计内容");
        input.addEventListener("input", () => {
            state.query = input.value.trim().toLocaleLowerCase();
            renderMatrix();
        });
        search.append(input);
        controls.append(search);
        const priority = makeSelect("优先级", [["all", "全部优先级"], ["P0", "P0"], ["P1", "P1"], ["P2", "P2"], ["待定", "待定"]], (value) => {
            state.priority = value;
            renderMatrix();
        });
        const projection = makeSelect("矩阵列", [["provider", "按厂商聚合"], ["model", "按统计模型（合并变体）"]], (value) => {
            state.projection = value;
            renderMatrix();
        });
        controls.append(projection);
        const selectedLabel = el("label", "bl-checkbox-label");
        refs.selectedOnly = el("input");
        refs.selectedOnly.type = "checkbox";
        refs.selectedOnly.addEventListener("change", () => {
            state.selectedOnly = refs.selectedOnly.checked;
            renderMatrix();
        });
        selectedLabel.append(refs.selectedOnly, el("span", "", "只看已选"));
        const additionsLabel = el("label", "bl-checkbox-label bl-additions-toggle");
        refs.additionsOnly = el("input");
        refs.additionsOnly.type = "checkbox";
        refs.additionsOnly.addEventListener("change", () => {
            state.additionsOnly = refs.additionsOnly.checked;
            renderMatrix();
        });
        additionsLabel.append(refs.additionsOnly, el("span", "", "只看补漏"));
        const toggles = el("div", "bl-filter-toggles");
        toggles.append(additionsLabel, selectedLabel);
        controls.append(toggles);
        parent.append(controls);
        const modes = el("div", "bl-mode-row");
        const group = el("div", "bl-segmented");
        group.setAttribute("role", "group");
        group.setAttribute("aria-label", "矩阵统计口径");
        refs.modeButtons = [];
        for (const [value, label] of [["verified", "已核实 · 发布方采用"]]) {
            const item = button(label, "", () => {
                state.mode = value;
                renderMatrix();
            });
            item.dataset.mode = value;
            refs.modeButtons.push(item);
            group.append(item);
        }
        modes.append(group, el("span", "bl-mode-hint", "点击数字或 Benchmark，逐条查看来源与修正建议"));
        modes.append(button("↗ 全屏引用趋势", "bl-button bl-trend-launch", (event) =>
            openTrends(event.currentTarget)));
        parent.append(modes);
    }

    function makeSelect(label, options, onChange) {
        const wrapper = el("label", "bl-select-label");
        wrapper.append(el("span", "visually-hidden", label));
        const select = el("select");
        select.setAttribute("aria-label", label);
        for (const [value, text] of options) {
            const option = el("option", "", text);
            option.value = value;
            select.append(option);
        }
        select.addEventListener("change", () => onChange(select.value));
        wrapper.append(select);
        return wrapper;
    }

    function categories() {
        const present = [...new Set(state.data.benchmarks.map((row) => row.category))];
        return [...CATEGORY_ORDER.filter((category) => present.includes(category)),
            ...present.filter((category) => !CATEGORY_ORDER.includes(category))];
    }

    function render() {
        withAuditCache(state.data, () => {
            renderStats();
            renderTabs();
            renderMatrix();
            renderSelection();
        });
    }

    function renderStats() {
        const rows = state.data.benchmarks;
        const edges = rows.reduce((sum, row) => sum + uniqueConfirmed(row).length, 0);
        const withEvidence = rows.filter((row) => uniqueConfirmed(row).length).length;
        const openClaims = rows.reduce((sum, row) => sum + rowOriginals(row).filter((name) =>
            !uniqueConfirmed(row).some((claim) => releaseKey(claim.countingModel) === releaseKey(name))).length, 0);
        const additions = filterAdditions(rows, true).length;
        refs.stats.replaceChildren();
        for (const [value, label, note] of [
            [rows.length, "Benchmark 条目", `${rows.length - additions} 项基线 · ${additions} 项新增补漏`],
            [edges, "窗口内已核实引用", "按 Benchmark × 统计模型去重"],
            [`${withEvidence}/${rows.length}`, "有发布采用证据", "窗口内至少一个模型自身引用"],
            [registry().length, "已登记型号", "含窗口外与日期待核实型号"],
        ]) {
            const stat = el("div", "bl-stat");
            stat.append(el("span", "bl-stat-label", label), el("strong", "bl-stat-value", value), el("small", "", note));
            refs.stats.append(stat);
        }
    }

    function renderTabs() {
        refs.tabs.replaceChildren();
        for (const category of ["all", ...categories()]) {
            const count = category === "all" ? state.data.benchmarks.length
                : state.data.benchmarks.filter((row) => row.category === category).length;
            const tab = button("", "bl-tab", () => {
                state.category = category;
                renderTabs();
                renderMatrix();
                [...refs.tabs.children].find((node) => node.dataset.category === category)?.focus();
            });
            tab.dataset.category = category;
            tab.setAttribute("role", "tab");
            tab.setAttribute("aria-controls", "blMatrixPanel");
            tab.setAttribute("aria-selected", String(state.category === category));
            tab.tabIndex = state.category === category ? 0 : -1;
            tab.append(el("span", "", category === "all" ? "全部板块" : CATEGORY_LABEL[category] || category),
                el("small", "", count));
            tab.addEventListener("keydown", (event) => {
                if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) {
                    return;
                }
                event.preventDefault();
                const buttons = [...refs.tabs.children];
                let index = buttons.indexOf(tab);
                index = event.key === "Home" ? 0 : event.key === "End" ? buttons.length - 1
                    : (index + (event.key === "ArrowRight" ? 1 : -1) + buttons.length) % buttons.length;
                buttons[index].click();
            });
            refs.tabs.append(tab);
        }
    }

    function filteredRows() {
        return filterAdditions(state.data.benchmarks, state.additionsOnly).filter((row) => {
            if (state.category !== "all" && row.category !== state.category) {
                return false;
            }
            if (state.priority !== "all" && row.priority !== state.priority) {
                return false;
            }
            if (state.selectedOnly && !state.selected.has(row.id)) {
                return false;
            }
            return matchesQuery(row, state.query);
        }).sort((a, b) => {
            const count = (row) => state.mode === "verified" ? uniqueConfirmed(row).length : rowOriginals(row).length;
            return count(b) - count(a) || a.priority.localeCompare(b.priority) || a.name.localeCompare(b.name);
        });
    }

    function matchesQuery(row, query, data = state.data) {
        return !query || [row.name, row.category, row.originalDescription, row.recommendedDescription,
            ...rowOriginals(row, data), ...reviews(row).filter((claim) => inScope(claim, data))
                .map((claim) => `${modelName(claim.model)} ${countingName(claim, data)} ${claim.note || ""}`)]
            .map(string).join(" ").toLocaleLowerCase().includes(query.toLocaleLowerCase());
    }

    function columnsFor(rows, projection = state.projection, data = state.data) {
        const entries = new Map();
        for (const release of registry(data).filter((item) => releaseScope(item, data).eligible)) {
            const model = modelName(release.countingModel || release.model);
            const key = columnFor(model, release.provider, projection);
            entries.set(key, projection === "model" ? model : key);
        }
        for (const row of rows) {
            for (const claim of reviews(row).filter((item) => inScope(item, data))) {
                const info = claimScope(claim, data);
                const model = info.countingModel;
                const key = columnFor(model, info.provider, projection);
                entries.set(key, projection === "model" ? model : key);
            }
            for (const model of rowOriginals(row, data)) {
                const matched = registryMatch(model, true, data);
                const key = columnFor(model, matched?.provider, projection);
                entries.set(key, projection === "model" ? model : key);
            }
        }
        return [...entries].sort(([keyA, labelA], [keyB, labelB]) => {
            const providerA = projection === "model" ? providerFor(labelA) : keyA;
            const providerB = projection === "model" ? providerFor(labelB) : keyB;
            const rank = (provider) => PROVIDERS.includes(provider) ? PROVIDERS.indexOf(provider) : PROVIDERS.length;
            return rank(providerA) - rank(providerB) || labelA.localeCompare(labelB);
        });
    }

    function scopeLabel(data = state.data) {
        const scope = data?.modelScope;
        return validDate(scope?.startDate) && validDate(scope?.endDate)
            ? `发布窗口 ${scope.startDate} — ${scope.endDate}` : "发布统计窗口尚未配置";
    }

    function registrySummary(data = state.data) {
        const releases = registry(data);
        const included = releases.filter((item) => releaseScope(item, data).eligible);
        return {releases, included, excluded: releases.filter((item) => !releaseScope(item, data).eligible),
            countingModels: [...new Set(included.map((item) => releaseKey(item.countingModel || item.model)))]};
    }

    function appendDateSources(parent, release) {
        for (const source of Array.isArray(release?.dateSources) ? release.dateSources : []) {
            sourceBlock(parent, typeof source === "string" ? source : source.url || source.sourceUrl,
                typeof source === "string" ? "发布日期来源" : source.title || "发布日期来源",
                typeof source === "string" ? "" : source.location);
        }
    }

    function openModelRegistry(opener) {
        closeDrawer(false);
        state.opener = opener;
        const overlay = el("div", "bl-drawer-overlay");
        const dialog = el("section", "bl-drawer bl-registry-drawer");
        dialog.setAttribute("role", "dialog");
        dialog.setAttribute("aria-modal", "true");
        dialog.setAttribute("aria-labelledby", "blRegistryTitle");
        dialog.tabIndex = -1;
        const top = el("div", "bl-drawer-top");
        const close = button("×", "bl-close", () => closeDrawer());
        close.setAttribute("aria-label", "关闭模型范围面板");
        top.append(el("span", "bl-eyebrow", "MODEL RELEASE SCOPE"), close);
        const title = el("h2", "", "模型范围与发布日期");
        title.id = "blRegistryTitle";
        dialog.append(top, title, el("p", "bl-drawer-subtitle", `${scopeLabel()}（含起止日）`));
        const summary = registrySummary();
        dialog.append(el("p", "bl-scope-explanation", `${summary.included.length} 个实际发布型号合并为 ${summary.countingModels.length} 个统计模型；另有 ${summary.excluded.length} 个型号暂不计数。GPT-5.6 Sol / Terra / Luna 合计一个，GPT-6 独立。官方仅公布月份时，整个日期范围落在窗口内才计数。符合窗口的模型即使暂无引用，也保留矩阵列。`));
        for (const [label, releases, included] of [
            ["本轮统计范围", summary.included, true], ["保留记录 · 不计入本轮", summary.excluded, false],
        ]) {
            const section = el("section", "bl-detail-section");
            section.append(el("h3", "", `${label} · ${releases.length} 个实际型号`));
            if (!releases.length) {
                section.append(el("p", "bl-muted", included ? "尚无日期与范围均已核实的模型。" : "暂无排除项。"));
            }
            const ordered = [...releases].sort((a, b) => string(releaseBounds(b)?.start).localeCompare(string(releaseBounds(a)?.start))
                || modelName(a.model).localeCompare(modelName(b.model)));
            for (const release of ordered) {
                const card = el("article", `bl-release-card${included ? "" : " bl-release-excluded"}`);
                const head = el("div", "bl-claim-head");
                head.append(el("strong", "", modelName(release.model)),
                    el("span", "bl-status", included ? "窗口内" : "不计数"));
                card.append(head, el("p", "bl-release-meta", `${providerFor(release.model, release.provider)} · 发布日期：${releaseDateLabel(release)}`),
                    el("p", "bl-claim-note", `统计模型：${modelName(release.countingModel || release.model)}`));
                if (release.scopeNote) {
                    card.append(el("p", "bl-claim-note", string(release.scopeNote)));
                }
                if (!included) {
                    card.append(el("p", "bl-scope-excluded", releaseScope(release).reason));
                }
                appendDateSources(card, release);
                section.append(card);
            }
            dialog.append(section);
        }
        mountDrawer(overlay, dialog);
    }

    function renderMatrix() {
        return withAuditCache(state.data, renderMatrixContent);
    }

    function matrixPage(rows, filters, previous = {}) {
        const filterKey = JSON.stringify([filters.projection, filters.category, filters.query, filters.priority,
            filters.mode, filters.selectedOnly, filters.additionsOnly]);
        const enabled = filters.projection === "model";
        const requested = previous.filterKey === filterKey && Number.isFinite(previous.page)
            ? Math.trunc(previous.page) : 0;
        const pageCount = Math.max(1, Math.ceil(rows.length / MODEL_PAGE_SIZE));
        const page = enabled ? Math.max(0, Math.min(requested, pageCount - 1)) : 0;
        const offset = enabled ? page * MODEL_PAGE_SIZE : 0;
        const visible = enabled ? rows.slice(offset, offset + MODEL_PAGE_SIZE) : rows;
        return {rows: visible, page, pageCount: enabled ? pageCount : 1, total: rows.length,
            start: rows.length ? offset + 1 : 0, end: offset + visible.length, enabled, filterKey};
    }

    function changePage(delta) {
        state.page += delta;
        renderMatrix();
        refs.matrix.scrollTop = 0;
        const preferred = delta > 0 ? refs.nextPage : refs.previousPage;
        const alternate = delta > 0 ? refs.previousPage : refs.nextPage;
        (preferred.disabled ? alternate : preferred).focus({preventScroll: true});
    }

    function renderMatrixContent() {
        const allRows = filteredRows();
        const page = matrixPage(allRows, state, {page: state.page, filterKey: state.pageFilterKey});
        state.page = page.page;
        state.pageFilterKey = page.filterKey;
        const rows = page.rows;
        // Columns, ranking and color scales describe every filtered row, independent of the visible page.
        const columns = columnsFor(allRows);
        const maxCell = Math.max(1, ...allRows.flatMap((row) => columns.map(([key]) => {
            const cell = cellSummary(row, key, state.projection);
            return state.mode === "verified" ? cell.confirmed.length : cell.originals.length;
        })));
        const maxRow = Math.max(1, ...allRows.map((row) => state.mode === "verified"
            ? uniqueConfirmed(row).length : rowOriginals(row).length));
        refs.modeButtons.forEach((item) => item.setAttribute("aria-pressed", String(item.dataset.mode === state.mode)));
        refs.legend.replaceChildren();
        refs.legend.append(el("span", "", state.mode === "verified" ? "已核实采用" : "原文提及"));
        for (let level = 1; level <= 4; level += 1) {
            const swatch = el("i", `bl-swatch bl-heat-${level}${state.mode === "original" ? " bl-original-swatch" : ""}`);
            swatch.setAttribute("aria-hidden", "true");
            refs.legend.append(swatch);
        }
        refs.legend.append(el("span", "", "少 → 多"), el("span", "bl-legend-unresolved", "仅显示已核实发布引用"),
            el("span", "", "— 暂无可计数证据"), el("span", "bl-legend-addition", "▰ 新增补漏（本周补充）"));
        refs.matrixSummaryText.textContent = `${allRows.length} 个 Benchmark · ${columns.length} 个${state.projection === "provider" ? "窗口内厂商" : "窗口内统计模型"} · 按${state.mode === "verified" ? "已核实引用" : "原文提及"}排序`;
        refs.pagination.hidden = !page.enabled || !page.total;
        refs.paginationStatus.textContent = `${page.start}–${page.end} / ${page.total}`;
        refs.previousPage.disabled = page.page === 0;
        refs.nextPage.disabled = page.page >= page.pageCount - 1;
        refs.previousPage.title = refs.previousPage.disabled ? "已到第一页" : "查看上一页 Benchmark";
        refs.nextPage.title = refs.nextPage.disabled ? "已到最后一页" : "查看下一页 Benchmark";
        refs.matrix.replaceChildren();
        if (!rows.length) {
            const empty = el("div", "bl-empty");
            empty.append(el("h3", "", "没有匹配的 Benchmark"), el("p", "", "试试其他关键词、优先级或板块。"));
            refs.matrix.append(empty);
            return;
        }
        const table = el("table", "bl-matrix");
        const caption = el("caption", "visually-hidden", `${state.mode === "verified" ? "已核实发布引用" : "原文提及"}矩阵。当前显示第 ${page.start}–${page.end} 条，共 ${page.total} 条。${scopeLabel()}，按统计模型去重；GPT-5.6 三个变体合计一个，GPT-6 独立。空白不等于未参评。`);
        table.append(caption);
        const head = el("thead");
        const header = el("tr");
        const nameHeader = el("th", "bl-name-column", "BENCHMARK / 优先级");
        nameHeader.scope = "col";
        header.append(nameHeader);
        const coverageHeader = el("th", "bl-coverage-column", "模型覆盖率");
        coverageHeader.append(el("small", "", "已核实采用"));
        coverageHeader.scope = "col";
        coverageHeader.title = "已核实引用模型数 ÷ 窗口内全部统计模型数；不随矩阵列或 Benchmark 筛选变化";
        header.append(coverageHeader);
        const countHeader = el("th", "bl-count-column", state.mode === "verified" ? "引用广度" : "原文提及");
        countHeader.scope = "col";
        header.append(countHeader);
        columns.forEach(([key, name]) => {
            const cell = el("th", `bl-provider-column${state.projection === "model" ? " bl-model-column" : ""}`);
            cell.scope = "col";
            cell.append(el("span", "", name));
            if (state.projection === "model") {
                cell.append(el("small", "", providerFor(name)));
            }
            cell.dataset.column = key;
            header.append(cell);
        });
        head.append(header);
        table.append(head);
        const body = el("tbody");
        rows.forEach((row) => {
            const tr = el("tr", row.isAddition === true ? "bl-row-addition" : "");
            const labelCell = el("th", "bl-name-column");
            labelCell.scope = "row";
            const label = el("div", "bl-row-label");
            const selected = state.selected.has(row.id);
            const star = button(selected ? "★" : "☆", "bl-star", () => {
                state.selected.has(row.id) ? state.selected.delete(row.id) : state.selected.add(row.id);
                persistSelection();
                renderMatrix();
                renderSelection();
            });
            star.setAttribute("aria-label", `${selected ? "从候选清单移除" : "加入候选清单"} ${row.name}`);
            star.setAttribute("aria-pressed", String(selected));
            const rowButton = button("", "bl-benchmark-name", (event) => openDrawer(row, null, event.currentTarget));
            rowButton.append(el("strong", "", row.name));
            const rowMeta = el("span", "bl-row-meta");
            rowMeta.append(
                el("span", "", CATEGORY_LABEL[row.category] || row.category));
            if (row.isAddition === true) {
                rowMeta.append(el("span", "bl-addition", "新增补漏"));
            }
            rowButton.append(rowMeta);
            label.append(star, rowButton);
            labelCell.append(label);
            tr.append(labelCell);
            const coverage = coverageSummary(row);
            const coverageCell = el("td", "bl-coverage-column");
            coverageCell.title = `已核实引用 ${coverage.count} / 窗口内全部 ${coverage.total} 个统计模型；仅统计发布方采用`;
            coverageCell.append(el("strong", "", formatPercent(coverage.percent)),
                el("small", "", `${coverage.count} / ${coverage.total}`));
            tr.append(coverageCell);
            const count = state.mode === "verified" ? uniqueConfirmed(row).length : rowOriginals(row).length;
            const broad = el("td", "bl-count-column");
            const bar = el("div", "bl-count-bar");
            const fill = el("span");
            fill.style.width = `${Math.round(count / maxRow * 100)}%`;
            bar.append(fill);
            broad.append(el("strong", "", count), bar);
            tr.append(broad);
            columns.forEach(([key, name]) => {
                const details = cellSummary(row, key, state.projection);
                const value = state.mode === "verified" ? details.confirmed.length : details.originals.length;
                const td = el("td", "bl-matrix-cell");
                const level = value ? Math.max(1, Math.ceil(value / maxCell * 4)) : 0;
                const cell = button(value ? String(value) : details.unresolved.length ? "◦" : "—",
                    `bl-cell-button bl-heat-${level}${state.mode === "original" ? " bl-original-cell" : ""}${details.unresolved.length ? " bl-has-unresolved" : ""}`,
                    (event) => openDrawer(row, {key, name, projection: state.projection}, event.currentTarget));
                const note = `${row.name} · ${name}：窗口内 ${details.confirmed.length} 个统计模型已核实引用，${details.originals.length} 个原文提及，${details.unresolved.length} 项待澄清`;
                cell.setAttribute("aria-label", `${note}。打开证据`);
                cell.title = note;
                if (value && details.unresolved.length) {
                    cell.append(el("span", "bl-unresolved-dot", "◦"));
                }
                td.append(cell);
                tr.append(td);
            });
            body.append(tr);
        });
        table.append(body);
        refs.matrix.append(table);
    }

    function trendPopulation(data = state.data) {
        return memoValue("trendPopulation", "window", () => {
            const models = new Map();
            for (const release of registry(data)) {
                if (releaseScope(release, data).eligible) {
                    const name = modelName(release.countingModel || release.model);
                    if (name && !models.has(releaseKey(name))) {
                        models.set(releaseKey(name), name);
                    }
                }
            }
            return models;
        }, data);
    }

    function coverageSummary(row, data = state.data) {
        const population = trendPopulation(data);
        const count = uniqueConfirmed(row, data).filter((claim) =>
            population.has(releaseKey(claim.countingModel))).length;
        const total = population.size;
        return {count, total, percent: total ? count / total * 100 : null};
    }

    function trendCalendarPeriods(data) {
        const scope = data?.modelScope;
        if (!validDate(scope?.startDate) || !validDate(scope?.endDate) || scope.startDate > scope.endDate) {
            return [];
        }
        const cursor = new Date(`${scope.startDate}T00:00:00Z`);
        cursor.setUTCDate(1);
        const periods = [];
        while (cursor.toISOString().slice(0, 10) <= scope.endDate) {
            const first = cursor.toISOString().slice(0, 10);
            const key = first.slice(0, 7);
            const label = `${cursor.getUTCMonth() + 1}月`;
            cursor.setUTCMonth(cursor.getUTCMonth() + 1);
            const last = new Date(cursor.valueOf() - 86400000).toISOString().slice(0, 10);
            const startDate = first < scope.startDate ? scope.startDate : first;
            const endDate = last > scope.endDate ? scope.endDate : last;
            periods.push({key, label, startDate, endDate, partial: first !== startDate || last !== endDate,
                total: 0, models: []});
        }
        return periods;
    }

    function trendReleaseMonth(release) {
        const dates = releaseBounds(release);
        return dates && dates.start.slice(0, 7) === dates.end.slice(0, 7) ? dates.start.slice(0, 7) : null;
    }

    function buildTrendData(rows, data = state.data) {
        return withAuditCache(data, () => {
            const periods = trendCalendarPeriods(data);
            const indexByMonth = new Map(periods.map((period, index) => [period.key, index]));
            const periodModels = periods.map(() => new Map());
            let excludedTimingCount = 0;
            for (const release of registry(data)) {
                if (!releaseScope(release, data).eligible) {
                    continue;
                }
                const month = trendReleaseMonth(release);
                if (!month) {
                    excludedTimingCount += 1;
                    continue;
                }
                const index = indexByMonth.get(month);
                const name = modelName(release.countingModel || release.model);
                if (index !== undefined && name && !periodModels[index].has(releaseKey(name))) {
                    periodModels[index].set(releaseKey(name), name);
                }
            }
            periods.forEach((period, index) => {
                period.models = [...periodModels[index].values()];
                period.total = period.models.length;
            });
            const completeIndexes = periods.map((period, index) => period.partial ? -1 : index)
                .filter((index) => index >= 0);
            let maxCount = 0;
            const trendRows = rows.map((row) => {
                const pointModels = periods.map(() => new Map());
                const points = periods.map((period) => ({count: 0, total: period.total,
                    percent: period.total ? 0 : null, models: [], claims: []}));
                for (const claim of reviews(row)) {
                    if (!isOwnConfirmed(claim, data)) {
                        continue;
                    }
                    // Use each actual release's date, not its merged family's first or latest date.
                    const info = claimScope(claim, data);
                    const index = indexByMonth.get(trendReleaseMonth(info));
                    const modelKey = releaseKey(info.countingModel);
                    if (index === undefined || !periodModels[index].has(modelKey)) {
                        continue;
                    }
                    pointModels[index].set(modelKey, periodModels[index].get(modelKey));
                    points[index].claims.push(claim);
                }
                points.forEach((point, index) => {
                    point.models = [...pointModels[index].values()];
                    point.count = point.models.length;
                    point.percent = point.total ? point.count / point.total * 100 : null;
                    maxCount = Math.max(maxCount, point.count);
                });
                let change = null;
                let countChange = null;
                if (completeIndexes.length >= 2) {
                    const first = points[completeIndexes[0]];
                    const last = points[completeIndexes[completeIndexes.length - 1]];
                    countChange = last.count - first.count;
                    if (first.percent !== null && last.percent !== null) {
                        change = last.percent - first.percent;
                    }
                }
                return {id: row.id, points, total: coverageSummary(row, data).count, change, countChange};
            });
            return {periods, rows: trendRows, maxCount, excludedTimingCount};
        });
    }

    function formatPercent(value) {
        return value === null || !Number.isFinite(value) ? "—" : `${value.toFixed(1)}%`;
    }

    function trendValue(point, metric) {
        return point.total ? (metric === "coverage" ? point.percent : point.count) : null;
    }

    function trendChange(series, metric) {
        const value = metric === "coverage" ? series.change : series.countChange;
        if (value === null || !Number.isFinite(value)) {
            return {text: "—", className: "", value: null};
        }
        return {text: `${value > 0 ? "+" : ""}${metric === "coverage" ? value.toFixed(1) : value}${metric === "coverage" ? " pp" : ""}`,
            className: value > 0 ? "bl-trend-up" : value < 0 ? "bl-trend-down" : "", value};
    }

    function trendSvg(series, periods, metric, maximum, large = false) {
        const width = large ? 640 : 132;
        const height = large ? 175 : 35;
        const padX = large ? 42 : 5;
        const top = large ? 22 : 5;
        const baseline = height - (large ? 32 : 5);
        const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
        svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
        svg.setAttribute("class", large ? "bl-trend-chart" : "bl-sparkline");
        svg.setAttribute("role", "img");
        svg.setAttribute("aria-label", periods.map((period, index) =>
            `${period.key}：${trendValue(series.points[index], metric) === null ? "无发布模型" : metric === "coverage"
                ? formatPercent(series.points[index].percent) : series.points[index].count}`).join("；"));
        const draw = (tag, attrs, text) => {
            const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
            Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, String(value)));
            if (text !== undefined) {
                node.textContent = text;
            }
            svg.append(node);
            return node;
        };
        const x = (index) => padX + index * (width - padX * 2) / Math.max(1, periods.length - 1);
        const y = (value) => baseline - value / Math.max(1, maximum) * (baseline - top);
        for (const value of large ? [0, maximum / 2, maximum] : [0]) {
            draw("line", {x1: padX, x2: width - padX, y1: y(value), y2: y(value), stroke: "#e6ebf4"});
            if (large) {
                draw("text", {x: padX - 8, y: y(value) + 3, "text-anchor": "end", fill: "#7b8498", "font-size": 9},
                    metric === "coverage" ? `${Math.round(value)}%` : String(Math.round(value * 10) / 10));
            }
        }
        series.points.forEach((point, index) => {
            const period = periods[index];
            const value = trendValue(point, metric);
            const previous = index ? trendValue(series.points[index - 1], metric) : null;
            if (index && value !== null && previous !== null) {
                draw("line", {x1: x(index - 1), x2: x(index), y1: y(previous), y2: y(value),
                    stroke: "currentColor", "stroke-width": large ? 2.5 : 1.8,
                    "stroke-dasharray": periods[index].partial || periods[index - 1].partial ? "4 3" : "none"});
            }
            if (value !== null) {
                draw("circle", {cx: x(index), cy: y(value), r: large ? 3.5 : 2,
                    fill: periods[index].partial ? "white" : "currentColor", stroke: "currentColor", "stroke-width": 1.5});
            }
            if (large) {
                draw("text", {x: x(index), y: height - 8, "text-anchor": "middle", fill: "#6b7892", "font-size": 10},
                    `${Number(period.key.slice(5))}月${period.partial ? "*" : ""}`);
                if (value !== null) {
                    draw("text", {x: x(index), y: y(value) - 9, "text-anchor": "middle", fill: "currentColor", "font-size": 10},
                        metric === "coverage" ? formatPercent(value) : String(value));
                }
            }
        });
        return svg;
    }

    function openTrends(opener) {
        closeDrawer(false);
        state.opener = opener;
        const overlay = el("div", "bl-drawer-overlay bl-trends-overlay");
        const dialog = el("section", "bl-drawer bl-trends-dialog");
        dialog.tabIndex = -1;
        dialog.setAttribute("role", "dialog");
        dialog.setAttribute("aria-modal", "true");
        dialog.setAttribute("aria-labelledby", "blTrendsTitle");
        const view = {metric: "count", sort: "breadth", query: state.query, category: state.category,
            additionsOnly: state.additionsOnly, selectedOnly: state.selectedOnly, selected: null, period: null,
            data: withAuditCache(state.data, () => buildTrendData(state.data.benchmarks)), dialog};
        const top = el("div", "bl-trends-top");
        const heading = el("div");
        heading.append(el("p", "bl-eyebrow", "BENCHMARK ADOPTION · SIX-MONTH VIEW"));
        const title = el("h2", "", "引用趋势");
        title.id = "blTrendsTitle";
        heading.append(title, el("p", "bl-trends-subtitle", `${scopeLabel()} · 只计已核实的发布方采用`));
        const close = button("退出全屏 ×", "bl-button", closeDrawer);
        close.setAttribute("aria-label", "关闭引用趋势");
        top.append(heading, close);
        dialog.append(top);
        const controls = el("div", "bl-trends-controls");
        const search = el("input", "bl-trend-search");
        search.type = "search";
        search.placeholder = "搜索 Benchmark…";
        search.value = view.query;
        search.setAttribute("aria-label", "搜索趋势 Benchmark");
        search.addEventListener("input", () => {view.query = search.value.trim().toLocaleLowerCase(); renderTrends(view);});
        const category = makeSelect("趋势板块", [["all", "全部板块"], ...categories().map((item) =>
            [item, CATEGORY_LABEL[item] || item])], (value) => {view.category = value; renderTrends(view);});
        category.querySelector("select").value = view.category;
        const metric = makeSelect("趋势指标", [["count", "引用模型数"], ["coverage", "当月模型覆盖率"]],
            (value) => {view.metric = value; renderTrends(view);});
        const sorting = makeSelect("趋势排序", [["breadth", "全期引用最多"], ["up", "增幅最大"],
            ["down", "降幅最大"], ["name", "按名称"]], (value) => {view.sort = value; renderTrends(view);});
        controls.append(search, category, metric, sorting);
        for (const [key, label] of [["additionsOnly", "只看补漏"], ["selectedOnly", "只看已选"]]) {
            const wrapper = el("label", "bl-checkbox-label");
            const checkbox = el("input");
            checkbox.type = "checkbox";
            checkbox.checked = view[key];
            checkbox.setAttribute("aria-label", `趋势${label}`);
            checkbox.addEventListener("change", () => {view[key] = checkbox.checked; renderTrends(view);});
            wrapper.append(checkbox, el("span", "", label));
            controls.append(wrapper);
        }
        dialog.append(controls);
        view.note = el("p", "bl-trends-note");
        dialog.append(view.note);
        view.summary = el("div", "bl-trends-summary");
        view.summary.setAttribute("aria-live", "polite");
        dialog.append(view.summary);
        view.scroll = el("div", "bl-trends-scroll");
        view.scroll.tabIndex = 0;
        view.scroll.setAttribute("role", "region");
        view.scroll.setAttribute("aria-label", "近六个月 Benchmark 引用趋势图，可滚动查看全部条目");
        dialog.append(view.scroll);
        view.detail = el("section", "bl-trend-detail");
        view.detail.setAttribute("aria-label", "选中 Benchmark 的月度明细");
        view.detail.hidden = true;
        dialog.append(view.detail);
        const foot = el("p", "bl-trends-footnote",
            "按实际型号发布日期归月，同一统计模型每月最多计一次；跨月变体可在不同月份出现，月数不可相加为全期去重数。当前是核验快照，报告可能晚发或更新，时间轴不代表网页首次引用日期。0 表示暂无可计数证据。紫色标记补漏。点击行看折线，点击月份看来源。");
        dialog.append(foot);
        renderTrends(view);
        mountDrawer(overlay, dialog);
    }

    function renderTrends(view) {
        const byId = new Map(state.data.benchmarks.map((row) => [row.id, row]));
        const complete = view.data.periods.filter((period) => !period.partial);
        const comparison = complete.length >= 2 ? `${complete[0].key} → ${complete.at(-1).key}` : "完整月份不足";
        const metricLabel = view.metric === "coverage" ? "当月模型覆盖率" : "当月引用模型数";
        const maximum = view.metric === "coverage" ? 100 : Math.max(1, view.data.maxCount);
        const rows = withAuditCache(state.data, () => view.data.rows.filter((series) => {
            const row = byId.get(series.id);
            return (view.category === "all" || row.category === view.category)
                && (!view.additionsOnly || row.isAddition) && (!view.selectedOnly || state.selected.has(row.id))
                && matchesQuery(row, view.query);
        }));
        rows.sort((a, b) => {
            if (view.sort === "name") {
                return byId.get(a.id).name.localeCompare(byId.get(b.id).name);
            }
            if (view.sort === "up" || view.sort === "down") {
                const av = trendChange(a, view.metric).value;
                const bv = trendChange(b, view.metric).value;
                if (av === null || bv === null) {
                    return av === bv ? b.total - a.total : av === null ? 1 : -1;
                }
                return (view.sort === "up" ? bv - av : av - bv) || b.total - a.total;
            }
            return b.total - a.total || byId.get(a.id).name.localeCompare(byId.get(b.id).name);
        });
        view.note.textContent = view.metric === "coverage"
            ? "月覆盖率 = 当月有引用证据的统计模型数 / 当月发布的全部统计模型数。各月发布数量不同，可用覆盖率辅助判断采用比例。"
            : "每格表示该月发布的模型中，有多少统计模型引用此 Benchmark。表头列出当月发布模型数；切换覆盖率可辅助比较发布量不同的月份。";
        view.summary.replaceChildren(el("span", "", `${rows.length} 个 Benchmark · ${metricLabel} · 增减比较完整月份 ${comparison}`));
        const legend = el("span", "bl-trend-legend");
        legend.append("少 ");
        for (let level = 0; level < 5; level += 1) {
            legend.append(el("i", `bl-swatch bl-heat-${level}`));
        }
        legend.append(` 多（${view.metric === "coverage" ? "0–100%" : `0–${maximum}` }） · * 部分月 · — 无发布模型`);
        view.summary.append(legend);
        if (view.data.excludedTimingCount) {
            view.summary.append(el("span", "", ` · ${view.data.excludedTimingCount} 条日期跨月不确定记录未归月`));
        }
        view.scroll.replaceChildren();
        if (!rows.length) {
            view.scroll.append(el("p", "bl-empty", "没有匹配的 Benchmark，请调整筛选条件。"));
        }
        else {
            const table = el("table", "bl-trends-table");
            table.append(el("caption", "visually-hidden", `近六个月 ${metricLabel}，${comparison} 比较增减；首尾部分月份不参与增减。`));
            const header = el("tr");
            const nameHeader = el("th", "bl-trend-name", "BENCHMARK");
            nameHeader.scope = "col";
            header.append(nameHeader);
            view.data.periods.forEach((period) => {
                const th = el("th", period.partial ? "bl-partial-month" : "");
                th.scope = "col";
                th.append(el("strong", "", `${Number(period.key.slice(5))}月${period.partial ? "*" : ""}`),
                    el("small", "", `${period.total} 个模型`));
                th.title = `${period.startDate} — ${period.endDate}${period.partial ? "（部分月）" : ""}`;
                if (period.partial) {
                    th.append(el("small", "bl-partial-label", `${Number(period.startDate.slice(8))}–${Number(period.endDate.slice(8))}日`));
                }
                header.append(th);
            });
            const shapeHeader = el("th", "bl-trend-shape", "月度走势");
            shapeHeader.scope = "col";
            const changeHeader = el("th", "bl-trend-change", "完整月增减");
            changeHeader.scope = "col";
            changeHeader.append(el("small", "", complete.length >= 2
                ? `${Number(complete[0].key.slice(5))}月 → ${Number(complete.at(-1).key.slice(5))}月` : "—"));
            changeHeader.title = view.metric === "coverage" ? "覆盖率百分点变化（pp），不是相对增长百分比" : "引用模型数量差";
            header.append(shapeHeader, changeHeader);
            const head = el("thead");
            head.append(header);
            table.append(head);
            const body = el("tbody");
            rows.forEach((series) => {
                const row = byId.get(series.id);
                const tr = el("tr", `${row.isAddition ? "bl-trend-addition " : ""}${view.selected === row.id ? "bl-trend-selected" : ""}`);
                tr.dataset.benchmark = row.id;
                const name = el("th", "bl-trend-name");
                name.scope = "row";
                const open = button("", "bl-benchmark-name", () => selectTrend(view, row.id, null));
                open.setAttribute("aria-label", `查看 ${row.name} 月度折线`);
                open.append(el("strong", "", row.name));
                const meta = el("span", "bl-row-meta", `${CATEGORY_LABEL[row.category] || row.category} · 全期 ${series.total} 个模型`);
                if (row.isAddition) {
                    meta.append(el("span", "bl-addition", "新增补漏"));
                }
                open.append(meta);
                name.append(open);
                tr.append(name);
                series.points.forEach((point, index) => {
                    const period = view.data.periods[index];
                    const value = trendValue(point, view.metric);
                    const td = el("td", period.partial ? "bl-partial-month" : "");
                    const level = value ? Math.min(4, Math.max(1, Math.ceil(value / maximum * 4))) : 0;
                    const label = value === null ? "—" : view.metric === "coverage" ? formatPercent(point.percent) : String(point.count);
                    const cell = button(label, `bl-trend-cell bl-heat-${level}`, () => selectTrend(view, row.id, index));
                    const text = `${row.name} · ${period.key}：${point.count} / ${point.total} 个统计模型，覆盖率 ${formatPercent(point.percent)}${period.partial ? "，部分月" : ""}`;
                    cell.title = text;
                    cell.setAttribute("aria-label", `${text}。查看当月证据`);
                    td.append(cell);
                    tr.append(td);
                });
                const shape = el("td", "bl-trend-shape");
                const shapeButton = button("", "bl-sparkline-button", () => selectTrend(view, row.id, null));
                shapeButton.setAttribute("aria-label", `展开 ${row.name} 趋势图`);
                shapeButton.append(trendSvg(series, view.data.periods, view.metric, maximum));
                shape.append(shapeButton);
                const delta = trendChange(series, view.metric);
                tr.append(shape, el("td", `bl-trend-change ${delta.className}`, delta.text));
                body.append(tr);
            });
            table.append(body);
            view.scroll.append(table);
        }
        if (view.selected && !rows.some((series) => series.id === view.selected)) {
            view.selected = null;
        }
        renderTrendDetail(view);
    }

    function selectTrend(view, id, index) {
        view.detailOpener = document.activeElement;
        view.selected = id;
        view.period = index;
        for (const row of view.scroll.querySelectorAll("tr[data-benchmark]")) {
            row.classList.toggle("bl-trend-selected", row.dataset.benchmark === id);
        }
        renderTrendDetail(view);
        view.detail.querySelector("button")?.focus({preventScroll: true});
    }

    function renderTrendDetail(view) {
        view.detail.hidden = !view.selected;
        view.detail.replaceChildren();
        if (!view.selected) {
            return;
        }
        const row = state.data.benchmarks.find((item) => item.id === view.selected);
        const series = view.data.rows.find((item) => item.id === view.selected);
        if (!row || !series || !view.data.periods.length) {
            view.detail.append(el("p", "bl-muted", "发布日期窗口尚未配置，暂时无法展示月度明细。"));
            return;
        }
        const periodIndex = view.period ?? Math.max(0, series.points.findLastIndex((point) => point.count));
        const period = view.data.periods[periodIndex];
        const point = series.points[periodIndex];
        const chart = el("div", "bl-trend-detail-chart");
        const top = el("div", "bl-trend-detail-top");
        const title = el("h3", "", row.name);
        if (row.isAddition) {
            title.append(el("span", "bl-addition", "新增补漏"));
        }
        const close = button("收起 ×", "bl-text-button", () => {
            const currentRowButton = view.scroll.querySelector(".bl-trend-selected .bl-benchmark-name");
            view.selected = null;
            renderTrendDetail(view);
            view.scroll.querySelector(".bl-trend-selected")?.classList.remove("bl-trend-selected");
            if (view.detailOpener?.isConnected) {
                view.detailOpener.focus({preventScroll: true});
            }
            else {
                (currentRowButton || view.scroll).focus({preventScroll: true});
            }
        });
        close.setAttribute("aria-label", "收起月度明细");
        top.append(title, close);
        chart.append(top, trendSvg(series, view.data.periods, view.metric,
            view.metric === "coverage" ? 100 : Math.max(1, view.data.maxCount), true));
        const evidence = el("div", "bl-trend-month-evidence");
        const periodSelect = makeSelect("明细月份", view.data.periods.map((item, index) =>
            [String(index), `${item.key}${item.partial ? "（部分月）" : ""}`]), (value) => {
                view.period = Number(value);
                renderTrendDetail(view);
                view.detail.querySelector("select")?.focus({preventScroll: true});
            });
        periodSelect.querySelector("select").value = String(periodIndex);
        evidence.append(periodSelect, el("strong", "bl-trend-month-total", `${point.count} / ${point.total} 个模型 · ${formatPercent(point.percent)}`));
        evidence.append(el("p", "bl-muted", `${period.startDate} — ${period.endDate}，按实际发布月统计。`));
        if (!point.claims.length) {
            evidence.append(el("p", "bl-muted", point.total ? "本月未取得可计数引用证据。" : "本月无符合范围的发布模型，覆盖率不定义。"));
        }
        const seen = new Set();
        for (const claim of point.claims) {
            const key = JSON.stringify([claim.model, claim.sourceUrl, claim.location]);
            if (seen.has(key)) {
                continue;
            }
            seen.add(key);
            const record = claimScope(claim);
            const card = el("div", "bl-trend-source-card");
            card.append(el("strong", "", `${record.countingModel}${record.countingModel !== claim.model ? ` · ${claim.model}` : ""}`),
                el("small", "", releaseDateLabel(record.record || claim)));
            sourceBlock(card, claim.sourceUrl, claim.sourceTitle || "发布原文", claim.location || claim.sourceLocation);
            appendScreenshot(card, claim);
            evidence.append(card);
        }
        view.detail.append(chart, evidence);
    }

    function renderSelection() {
        refs.shortlist.replaceChildren();
        const selected = state.data.benchmarks.filter((row) => state.selected.has(row.id));
        if (!selected.length) {
            refs.shortlist.append(el("p", "bl-muted", "还没有选择。先从已核实的引用和能力覆盖开始。"));
        }
        for (const row of selected) {
            const chip = button(`${row.name}  ×`, "bl-selection-chip", () => {
                state.selected.delete(row.id);
                persistSelection();
                renderMatrix();
                renderSelection();
            });
            chip.setAttribute("aria-label", `移除 ${row.name}`);
            refs.shortlist.append(chip);
        }
        refs.selectionStatus.textContent = `已选 ${selected.length} 项 · ${state.storageAvailable
            ? "当前浏览器保存" : "浏览器未允许保存，刷新后需重新选择"}`;
    }

    async function copySelection() {
        const selected = state.data.benchmarks.filter((row) => state.selected.has(row.id));
        const content = selected.length ? `${scopeLabel()}；GPT-5.6 三个变体合计一个，GPT-6 独立。\n\n`
            + selected.map((row) => `${row.name} — ${uniqueConfirmed(row).length} 个窗口内统计模型已核实引用\n${string(row.recommendedDescription || row.valueReview)}`).join("\n\n") : "";
        if (!content) {
            refs.selectionStatus.textContent = "请先选择至少一个 Benchmark。";
            return;
        }
        try {
            await navigator.clipboard.writeText(content);
            refs.selectionStatus.textContent = `已复制 ${selected.length} 项候选。`;
        }
        catch (_error) {
            const area = el("textarea", "bl-copy-fallback");
            area.value = content;
            area.setAttribute("aria-label", "候选清单，可手动复制");
            refs.shortlist.append(area);
            area.focus();
            area.select();
            refs.selectionStatus.textContent = "请选择文本后复制。";
        }
    }

    function openDrawer(row, column, opener) {
        closeDrawer(false);
        state.opener = opener;
        const overlay = el("div", "bl-drawer-overlay");
        const dialog = el("section", "bl-drawer");
        dialog.setAttribute("role", "dialog");
        dialog.setAttribute("aria-modal", "true");
        dialog.setAttribute("aria-labelledby", "blEvidenceTitle");
        dialog.tabIndex = -1;
        const top = el("div", "bl-drawer-top");
        top.append(el("span", "bl-eyebrow", "EVIDENCE RECORD"), button("×", "bl-close", () => closeDrawer()));
        top.lastChild.setAttribute("aria-label", "关闭证据面板");
        dialog.append(top);
        const title = el("h2", "", row.name);
        title.id = "blEvidenceTitle";
        dialog.append(title);
        if (row.isAddition === true) {
            dialog.append(el("span", "bl-addition bl-drawer-addition", "新增补漏 · 本周补充"));
        }
        dialog.append(el("p", "bl-drawer-subtitle", `${CATEGORY_LABEL[row.category] || row.category}${column ? ` · ${column.name}` : ""}`));
        const evidenceCount = uniqueConfirmed(row).length;
        const overview = el("div", "bl-evidence-summary");
        overview.append(el("strong", "", `${evidenceCount} 个`), el("span", "", "窗口内统计模型的自身发布采用已核实"));
        dialog.append(overview);
        dialog.append(el("p", "bl-scope-explanation", `${scopeLabel()}。GPT-5.6 三个变体合计一个，GPT-6 独立。下方保留实际型号、窗口外记录和未核实日期的证据；这些记录不增加矩阵计数。`));
        if (column) {
            const allButton = button("查看此 Benchmark 的全部模型证据", "bl-text-button", () => openDrawer(row, null, state.opener));
            dialog.append(allButton);
        }
        const evaluation = el("section", "bl-detail-section");
        evaluation.append(el("h3", "", "Benchmark 说明与公开来源"));
        if (row.descriptionStatus) {
            detailField(evaluation, "描述核查", STATUS[row.descriptionStatus] || row.descriptionStatus);
        }
        detailField(evaluation, "建议描述", row.recommendedDescription || "尚无修订建议");
        if (row.valueReview) {
            detailField(evaluation, "价值判断", row.valueReview);
        }
        if (row.reason) {
            detailField(evaluation, "补充理由", row.reason);
        }
        if (Array.isArray(row.issues) && row.issues.length) {
            detailField(evaluation, "需要注意", row.issues.map((issue) => typeof issue === "object" ? issue.note || issue.description || string(issue) : issue).join("\n"));
        }
        for (const source of row.descriptionSources || []) {
            sourceBlock(evaluation, source.url || source.sourceUrl, source.title || "Benchmark 第一方说明", source.location);
        }
        dialog.append(evaluation);
        const claimsSection = el("section", "bl-detail-section");
        claimsSection.append(el("h3", "", "逐模型引用核查"));
        const allReviews = reviews(row);
        const covered = new Set(allReviews.map((claim) => releaseKey(countingName(claim))));
        for (const model of rowOriginals(row)) {
            if (!covered.has(releaseKey(model))) {
                allReviews.push({model, status: "unverified", kind: "unknown", note: "原文有此记录，本轮尚无对应的可核验发布证据。"});
            }
        }
        const shown = allReviews.filter((claim) => {
            const info = claimScope(claim);
            return !column || columnFor(info.countingModel, info.provider, column.projection) === column.key;
        });
        shown.sort((a, b) => Number(isOwnConfirmed(b)) - Number(isOwnConfirmed(a)) || modelName(a.model).localeCompare(modelName(b.model)));
        if (!shown.length) {
            claimsSection.append(el("p", "bl-muted", "本轮未记录该交叉项的发布证据。这不等于该模型从未使用此 Benchmark。"));
        }
        for (const claim of shown) {
            const card = el("article", `bl-claim bl-claim-${claim.status || "unverified"}`);
            const heading = el("div", "bl-claim-head");
            heading.append(el("strong", "", modelName(claim.model)), el("span", "bl-status", STATUS[claim.status] || "待核实"));
            const info = claimScope(claim);
            card.append(heading, el("p", "bl-claim-kind", `${KIND[claim.kind] || KIND.unknown} · ${isOwnConfirmed(claim) ? "计入窗口内发布引用（同统计模型只计一次）" : "不计入已核实采用次数"}`),
                el("p", "bl-release-meta", `发布日期：${releaseDateLabel(info)} · 统计模型：${info.countingModel}`));
            if (!info.eligible) {
                card.append(el("p", "bl-scope-excluded", `范围排除：${info.reason}`));
            }
            if (info.record?.dateSources?.length) {
                const dateDetails = el("details", "bl-date-evidence");
                dateDetails.append(el("summary", "", "查看发布日期依据"));
                appendDateSources(dateDetails, info.record);
                card.append(dateDetails);
            }
            if (claim.correctedBenchmark) {
                card.append(el("p", "bl-correction", `应区分 / 修正为：${string(claim.correctedBenchmark)}`));
            }
            card.append(el("p", "bl-claim-note", claim.note || "暂无补充说明。"));
            sourceBlock(card, claim.sourceUrl, claim.sourceTitle || "原始发布来源", claim.location);
            for (const source of claim.sources || []) {
                sourceBlock(card, source.url || source.sourceUrl, source.title || "补充来源", source.location);
            }
            appendScreenshot(card, claim);
            claimsSection.append(card);
        }
        dialog.append(claimsSection);
        const footer = el("div", "bl-drawer-footer");
        if (globalThis.KW_BENCH_PUBLIC_MODE !== true) {
            appendLink(footer, "返回知识库原文 ↗", state.data.sourceDocument?.url);
        }
        footer.append(el("p", "bl-muted", "原始证据按实际型号逐条保留，矩阵按窗口内统计模型去重。空白或范围排除不代表该模型从未参加评测。"));
        dialog.append(footer);
        mountDrawer(overlay, dialog);
    }

    function mountDrawer(overlay, dialog) {
        overlay.append(dialog);
        overlay.addEventListener("click", (event) => {
            if (event.target === overlay) {
                closeDrawer();
            }
        });
        overlay.addEventListener("keydown", (event) => {
            if (event.key === "Escape") {
                event.preventDefault();
                closeDrawer();
            }
            if (event.key === "Tab") {
                const focusable = [...dialog.querySelectorAll("button, a[href], input, select, textarea, summary, [tabindex='0']")]
                    .filter((node) => !node.disabled && !node.closest("[hidden]")
                        && (!node.closest("details:not([open])") || node.tagName === "SUMMARY"));
                const first = focusable[0];
                const last = focusable[focusable.length - 1];
                if (event.shiftKey && (document.activeElement === first || document.activeElement === dialog)) {
                    event.preventDefault();
                    last?.focus();
                }
                else if (!event.shiftKey && document.activeElement === last) {
                    event.preventDefault();
                    first?.focus();
                }
            }
        });
        document.body.append(overlay);
        document.body.classList.add("bl-drawer-open");
        for (const node of [document.querySelector(".site-nav"), document.querySelector(".app-shell")]) {
            if (node) {
                node.inert = true;
            }
        }
        state.drawer = overlay;
        dialog.focus();
    }

    function detailField(parent, label, value) {
        const block = el("div", "bl-detail-field");
        block.append(el("span", "bl-detail-label", label), el("p", "", value));
        parent.append(block);
    }

    function sourceBlock(parent, url, title, locationText) {
        const block = el("div", "bl-source");
        appendLink(block, `${string(title)} ↗`, url);
        if (locationText) {
            block.append(el("p", "bl-source-location", `定位：${string(locationText)}`));
        }
        if (!safeUrl(url)) {
            block.append(el("span", "bl-muted", "尚无可直接核验的来源链接"));
        }
        parent.append(block);
    }

    function appendScreenshot(parent, claim) {
        const paths = [claim.screenshot, claim.screenshotPath,
            ...(Array.isArray(claim.screenshots) ? claim.screenshots : []),
            ...(Array.isArray(claim.evidence) ? claim.evidence : [])];
        const shown = new Set();
        for (const value of paths.filter(Boolean)) {
            const raw = typeof value === "object" ? value.path || value.url : value;
            const url = safeUrl(raw, true);
            if (!url || shown.has(url)) {
                continue;
            }
            shown.add(url);
            const caption = typeof value === "object" && value.caption
                ? string(value.caption) : "原文位置截图";
            const details = el("details", "bl-screenshot");
            details.append(el("summary", "", `查看截图 · ${caption}`));
            const img = el("img");
            img.alt = `${modelName(claim.model)} · ${caption}`;
            img.loading = "lazy";
            details.addEventListener("toggle", () => {
                if (details.open && !img.src) {
                    img.src = url;
                }
            });
            const imageLink = link("", url, "bl-screenshot-image", true);
            imageLink.setAttribute("aria-label", `打开完整截图：${caption}`);
            imageLink.append(img);
            details.append(imageLink);
            appendLink(details, "打开完整截图 ↗", url, "bl-source-link", true);
            if (typeof value === "object" && value.sourceUrl) {
                appendLink(details, "查看截图来源 ↗", value.sourceUrl);
            }
            parent.append(details);
        }
    }

    function closeDrawer(restoreFocus = true) {
        if (!state.drawer) {
            return;
        }
        state.drawer.remove();
        state.drawer = null;
        document.body.classList.remove("bl-drawer-open");
        for (const node of [document.querySelector(".site-nav"), document.querySelector(".app-shell")]) {
            if (node) {
                node.inert = false;
            }
        }
        if (restoreFocus && state.opener?.isConnected) {
            state.opener.focus({preventScroll: true});
        }
    }

    globalThis.KwBenchList = {
        activate,
        deactivate,
        focusSearch: () => {
            if (!state.drawer) {
                refs.search?.focus();
            }
        },
        testContracts: {releaseKey, providerFor, originals, rowOriginals, reviews, isOwnConfirmed,
            uniqueConfirmed, cellSummary, categoryFor, normalizeData, safeUrl, columnsFor, filterAdditions,
            validDate, releaseBounds, releaseDateLabel, releaseScope, claimScope, inScope, countingName, matchesQuery, registrySummary, scopeLabel,
            withAuditCache, matrixPage, coverageSummary, buildTrendData, trendValue, trendChange},
    };
})();
