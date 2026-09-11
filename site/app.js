"use strict";

const CATALOG_CANDIDATES = [
    "data/catalog.json",
    "data/index.json",
    "data/manifest.json",
    "../pdf_sample_dashboard/competitor_benches.json",
];
const KNOWLEDGE_COVERAGE_CANDIDATES = ["data/kw_coverage.json"];
const MIRROR_MANIFEST_CANDIDATES = ["data/mirror_manifest.json"];
const MIRROR_INDEX_CANDIDATES = ["assets/mirror_index.json"];
const PREVIEW_INDEX_CANDIDATES = ["assets/preview_index.json"];
const VERIFIER_SOURCE_INDEX_CANDIDATES = [
    "assets/verifier_source_index.json",
    "data/verifier_source_index.json",
];
const TRUSTED_HTML_SECURITY_PROFILE = "sandbox-no-same-origin-csp-network-none-v1";
const TRUSTED_SPREADSHEET_SECURITY_PROFILE = "static-workbook-safe-v1";
const SPREADSHEET_MANIFEST_MAX_BYTES = 16 * 1024 * 1024;
const SPREADSHEET_CHUNK_MAX_BYTES = 2 * 1024 * 1024;
const TASK_BATCH_SIZE = 60;
const GOLD_PROVENANCE_BATCH_SIZE = 20;
const TEXT_PREVIEW_CHARS = 256 * 1024;
const LOCAL_TEXT_CACHE_LIMIT = 3;
const INFLUENCE_GROUPS = [
    {
        tier: 1,
        title: "已进入模型厂商 Watchlist",
        shortTitle: "厂商 Watchlist",
        description: "进入头部模型技术报告、system card 或稳定能力报告。",
    },
    {
        tier: 2,
        title: "顶级独立评测 / 成熟社区",
        shortTitle: "强机构榜单",
        description: "由强评测机构或成熟社区持续运营并产生可比结果。",
    },
    {
        tier: 3,
        title: "机构强 / 方法有影响",
        shortTitle: "学术采用",
        description: "方法、论文或后续采用形成外部影响，但尚非固定 Watchlist。",
    },
    {
        tier: 4,
        title: "高相关 / 新兴待观察",
        shortTitle: "新兴待观察",
        description: "任务与 PDF Ops 高度同构，外部采用仍需时间验证。",
    },
];
const COVERAGE_STATUS_META = {
    full_public_indexed: {
        label: "全量公开 · 已索引",
        incompleteLabel: "全量公开 · 补录中",
        group: "public",
    },
    public_subset_indexed: {
        label: "公开范围 · 已索引",
        incompleteLabel: "公开范围 · 补录中",
        group: "public",
    },
    gated_terms_metadata_only: {
        label: "Gated · 仅元数据",
        group: "metadata",
    },
    unlicensed_metadata_only: {
        label: "无许可 · 仅元数据",
        group: "metadata",
    },
    paper_only_no_release: {
        label: "论文已出 · 数据未放",
        group: "excluded",
    },
    closed_excluded: {
        label: "正式集闭源 · 已排除",
        group: "excluded",
    },
};
const DELIVERABLE_LABELS = new Map([
    ["pdf", "PDF"],
    ["presentation", "PPT"],
    ["spreadsheet", "Excel"],
    ["document", "Word"],
    ["html", "HTML / Web"],
    ["image", "Image"],
    ["data_other", "Data / Other"],
    ["text", "QA / Text"],
    ["other", "Other"],
]);
const FORMAT_TO_DELIVERABLE = new Map([
    ["pdf", "pdf"],
    ["ppt", "presentation"],
    ["pptx", "presentation"],
    ["slides", "presentation"],
    ["xlsx", "spreadsheet"],
    ["xls", "spreadsheet"],
    ["csv", "spreadsheet"],
    ["doc", "document"],
    ["docx", "document"],
    ["html", "html"],
    ["htm", "html"],
    ["web", "html"],
    ["svg", "image"],
    ["png", "image"],
    ["jpg", "image"],
    ["jpeg", "image"],
    ["webp", "image"],
    ["gif", "image"],
    ["txt", "text"],
    ["md", "text"],
    ["json", "data_other"],
    ["jsonl", "data_other"],
    ["zip", "data_other"],
    ["video", "data_other"],
]);
const OFFICEQA_VARIANT_OPTIONS = [
    {id: "questions", label: "全部题目", unitKind: "question"},
    {id: "full", label: "Full", variantId: "full"},
    {id: "pro_original", label: "原 Pro", variantId: "pro_original"},
    {id: "pro_v2", label: "Pro V2", variantId: "pro_v2"},
    {id: "protocol", label: "实验协议", variantId: "protocol"},
];
const LOCAL_URL_PROTOCOLS = new Set(["http:", "https:"]);
const localTextCache = new Map();
const verifierTextCache = new Map();
let interactiveId = 0;

const state = {
    catalog: null,
    catalogUrl: "",
    knowledgeCoverage: null,
    knowledgeCoverageError: "",
    benches: [],
    embeddedBenches: new Map(),
    loadedBenches: new Map(),
    activeBenchId: "",
    activeBench: null,
    activeTaskId: "",
    taskViews: [],
    filteredTasks: [],
    renderedTaskCount: 0,
    benchSearch: "",
    relevanceFilter: "",
    deliverableFilter: "",
    taskSearch: "",
    taskCategory: "",
    taskDeliverable: "",
    taskVariant: "",
    fetchController: null,
    retryAction: null,
    globalMirrorManifest: null,
    benchMirrorManifest: null,
    mirrorIndex: null,
    previewIndex: null,
    verifierSourceIndex: null,
    mirrorRecordsByBench: new Map(),
    previewRecordsByBench: new Map(),
    verifierSourcesByTask: new Map(),
    loadedAssetShardUrls: new Set(),
    assetShardPromises: new Map(),
    taskDetailPromises: new Map(),
    assetSelectionToken: 0,
    assetIndexesLoaded: false,
    assetIndexLoadPromise: null,
    taskObserver: null,
};

const dom = {};

document.addEventListener("DOMContentLoaded", initialize);

function initialize() {
    cacheDom();
    bindEvents();
    configureTaskObserver();
    handleHashChange();
    loadCatalog();
}

function cacheDom() {
    [
        "mobileMenuButton", "sidebarScrim", "benchSidebar", "sidebarClose", "benchSearch",
        "resetBenchFilters", "relevanceFilters", "deliverableFilter", "benchGroups",
        "navBenchCount", "navStatusDot", "navStatusText", "catalogHome", "catalogStats",
        "tierOverview", "auditSummary", "auditTableBody", "coverageAudit", "exploreFirstBench",
        "jumpToAudit", "heroTrackedCount", "knowledgeCoverage",
        "knowledgeCoverageStatus",
        "knowledgeCoverageStats", "coverageCollisionGrid", "knowledgeCoverageTableBody",
        "knowledgeCoverageCards", "benchWorkspace", "benchHero", "benchAuditCard",
        "benchAuditCaption", "benchAuditBody", "taskSearch", "taskCategoryFilter",
        "taskDeliverableFilter", "taskVariantRow", "taskVariantFilters",
        "taskResultSummary", "renderModeLabel", "taskList",
        "taskSentinel", "loadMoreTasks", "taskEmptyState", "taskInspector", "fatalState",
        "fatalMessage", "fatalRetry", "loadingLayer", "loadingKicker", "loadingTitle",
        "loadingMessage", "progressTrack", "progressBar", "progressValue", "progressBytes",
        "loadingRetry", "benchButtonTemplate",
    ].forEach((id) => {
        dom[id] = document.getElementById(id);
    });
}

function bindEvents() {
    dom.mobileMenuButton.addEventListener("click", () => setSidebarOpen(true));
    dom.sidebarClose.addEventListener("click", () => setSidebarOpen(false));
    dom.sidebarScrim.addEventListener("click", () => setSidebarOpen(false));

    dom.benchSearch.addEventListener("input", () => {
        state.benchSearch = dom.benchSearch.value.trim().toLocaleLowerCase();
        renderBenchSidebar();
    });
    dom.deliverableFilter.addEventListener("change", () => {
        state.deliverableFilter = dom.deliverableFilter.value;
        renderBenchSidebar();
    });
    dom.relevanceFilters.addEventListener("click", (event) => {
        const button = event.target.closest("[data-relevance]");
        if (!button) {
            return;
        }
        state.relevanceFilter = button.dataset.relevance || "";
        updateRelevanceButtons();
        renderBenchSidebar();
    });
    dom.resetBenchFilters.addEventListener("click", resetBenchFilters);

    dom.exploreFirstBench.addEventListener("click", () => {
        if (state.benches[0]) {
            selectBench(state.benches[0].id);
        }
    });
    dom.jumpToAudit.addEventListener("click", () => {
        dom.knowledgeCoverage.open = true;
        dom.knowledgeCoverage.scrollIntoView({behavior: "smooth", block: "start"});
    });

    dom.taskSearch.addEventListener("input", debounce(() => {
        state.taskSearch = dom.taskSearch.value.trim().toLocaleLowerCase();
        filterAndRenderTasks();
    }, 120));
    dom.taskCategoryFilter.addEventListener("change", () => {
        state.taskCategory = dom.taskCategoryFilter.value;
        filterAndRenderTasks();
    });
    dom.taskDeliverableFilter.addEventListener("change", () => {
        state.taskDeliverable = dom.taskDeliverableFilter.value;
        filterAndRenderTasks();
    });
    dom.taskVariantFilters.addEventListener("click", (event) => {
        const button = event.target.closest("[data-task-variant]");
        if (!button) {
            return;
        }
        setTaskVariant(button.dataset.taskVariant || "questions", {
            updateLocation: true,
        });
    });
    dom.loadMoreTasks.addEventListener("click", renderNextTaskBatch);
    dom.fatalRetry.addEventListener("click", loadCatalog);
    dom.loadingRetry.addEventListener("click", () => {
        if (typeof state.retryAction === "function") {
            state.retryAction();
        }
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "/" && !isTypingTarget(event.target)) {
            event.preventDefault();
            if (window.innerWidth <= 960) {
                setSidebarOpen(true);
            }
            dom.benchSearch.focus({preventScroll: true});
        }
        if (event.key === "Escape") {
            setSidebarOpen(false);
        }
    });
    window.addEventListener("hashchange", handleHashChange);
}

function configureTaskObserver() {
    if (!("IntersectionObserver" in window)) {
        return;
    }
    state.taskObserver = new IntersectionObserver((entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
            renderNextTaskBatch();
        }
    }, {rootMargin: "480px 0px"});
    state.taskObserver.observe(dom.taskSentinel);
}

async function loadCatalog() {
    abortActiveFetch();
    state.retryAction = loadCatalog;
    hideFatalState();
    showLoader({
        kicker: "CATALOG · STAGE 1 / 2",
        title: "正在打开评测目录",
        message: "先读取轻量索引；题库只在你选择 Bench 后加载。",
    });
    setNavStatus("loading", "读取目录");

    let lastError = null;
    for (const candidate of CATALOG_CANDIDATES) {
        try {
            updateLoader({message: `尝试目录 ${candidate}`, indeterminate: true});
            const payload = await fetchJsonWithProgress(candidate, (progress) => {
                updateLoaderProgress(progress, "目录索引");
            });
            const catalog = normalizeCatalog(payload, candidate);
            if (!catalog.benches.length) {
                throw new Error("目录中没有 Benchmark 记录");
            }
            state.catalog = catalog;
            state.catalogUrl = candidate;
            state.benches = catalog.benches;
            state.embeddedBenches = catalog.embeddedBenches;
            finishCatalogLoad();
            hideLoader();
            void loadOptionalAssetData(catalog);
            handleHashChange();
            return;
        }
        catch (error) {
            if (error.name === "AbortError") {
                return;
            }
            lastError = error;
        }
    }

    const message = lastError?.message || "没有找到可读取的 catalog.json。";
    setNavStatus("error", "目录读取失败");
    showLoaderError("目录没有加载成功", message, loadCatalog);
    showFatalState(message);
}

function finishCatalogLoad() {
    dom.navBenchCount.textContent = `${formatNumber(state.benches.length)} Benches`;
    setNavStatus("ready", "目录已就绪");
    renderBenchSidebar();
    renderCatalogHome();
    void loadKnowledgeCoverage();
}

async function loadKnowledgeCoverage() {
    state.knowledgeCoverageError = "";
    for (const candidate of KNOWLEDGE_COVERAGE_CANDIDATES) {
        if (!isLocalUrl(candidate)) {
            continue;
        }
        try {
            const payload = await fetchJson(candidate);
            if (!Array.isArray(payload?.items) || payload.items.length !== 22) {
                throw new Error("审计矩阵必须包含 22 个知识库条目");
            }
            state.knowledgeCoverage = payload;
            renderKnowledgeCoverage();
            return;
        }
        catch (error) {
            state.knowledgeCoverageError = error?.message || "公开审计文件读取失败";
        }
    }
    renderKnowledgeCoverage();
}

async function loadOptionalMirrorManifest(catalog) {
    const declared = firstString(
        catalog.raw?.mirror_manifest_url,
        catalog.raw?.mirror_manifest,
        catalog.raw?.preview_manifest_url,
    );
    const candidates = declared ? [declared, ...MIRROR_MANIFEST_CANDIDATES] : MIRROR_MANIFEST_CANDIDATES;
    for (const candidate of candidates) {
        if (!isLocalUrl(candidate)) {
            continue;
        }
        try {
            state.globalMirrorManifest = await fetchJson(candidate);
            if (state.activeBench) {
                applyMirrorPlan(state.activeBench);
                renderBenchHero(state.activeBench);
                renderBenchAudit(state.activeBench);
            }
            if (state.activeTaskId) {
                renderTaskInspector(getActiveTaskView());
            }
            return;
        }
        catch (_error) {
            // Optional mirrors are allowed to be absent while data is still materializing.
        }
    }
}

async function loadOptionalAssetData(catalog) {
    if (state.assetIndexLoadPromise) {
        return state.assetIndexLoadPromise;
    }
    state.assetIndexLoadPromise = Promise.allSettled([
        loadOptionalMirrorManifest(catalog),
        loadOptionalAssetIndexes(),
    ]).then(() => {
        state.assetIndexesLoaded = true;
        state.benches.forEach(applyMirrorPlan);
        state.loadedBenches.forEach(applyMirrorPlan);
        renderCatalogHome();
        if (state.activeBench) {
            renderBenchHero(state.activeBench);
            renderBenchAudit(state.activeBench);
        }
        if (state.activeTaskId) {
            void selectTask(state.activeTaskId, {updateLocation: false, scroll: false});
        }
    });
    return state.assetIndexLoadPromise;
}

async function loadOptionalAssetIndexes() {
    const [mirrorResult, previewResult, verifierResult] = await Promise.allSettled([
        fetchFirstLocalJson(MIRROR_INDEX_CANDIDATES),
        fetchFirstLocalJson(PREVIEW_INDEX_CANDIDATES),
        fetchFirstLocalJson(VERIFIER_SOURCE_INDEX_CANDIDATES),
    ]);
    if (mirrorResult.status === "fulfilled" && mirrorResult.value) {
        state.mirrorIndex = mirrorResult.value;
        state.mirrorRecordsByBench = indexAssetRecords(mirrorResult.value);
    }
    if (previewResult.status === "fulfilled" && previewResult.value) {
        state.previewIndex = previewResult.value;
        state.previewRecordsByBench = indexAssetRecords(previewResult.value);
    }
    if (verifierResult.status === "fulfilled" && verifierResult.value) {
        state.verifierSourceIndex = verifierResult.value;
        state.verifierSourcesByTask = indexVerifierSources(verifierResult.value);
    }
}

async function fetchFirstLocalJson(candidates) {
    let lastError = null;
    for (const candidate of candidates) {
        if (!isLocalUrl(candidate)) {
            continue;
        }
        try {
            return await fetchJson(candidate);
        }
        catch (error) {
            lastError = error;
        }
    }
    if (lastError) {
        throw lastError;
    }
    return null;
}

function indexAssetRecords(payload) {
    const byBench = new Map();
    asArray(payload?.records).forEach((record) => {
        const benchId = firstString(record?.bench_id, record?.benchmark_id, record?.bench);
        if (!benchId) {
            return;
        }
        if (!byBench.has(benchId)) {
            byBench.set(benchId, []);
        }
        byBench.get(benchId).push(record);
    });
    return byBench;
}

function indexVerifierSources(payload) {
    const byTask = new Map();
    const records = [
        ...asArray(payload?.records),
        ...asArray(payload?.items),
        ...asArray(payload?.sources),
    ];
    const byTaskObject = payload?.by_task && typeof payload.by_task === "object"
        ? Object.entries(payload.by_task).map(([taskId, value]) => (
            value && typeof value === "object"
                ? {task_id: taskId, ...value}
                : {task_id: taskId, content: value}
        ))
        : [];
    [...records, ...byTaskObject].forEach((record) => {
        if (!record || typeof record !== "object") {
            return;
        }
        const benchId = firstString(record.bench_id, record.benchmark_id, record.bench);
        const taskIds = uniqueStrings([
            record.task_id,
            record.task_key,
            record.uid,
            ...asArray(record.task_ids),
        ]);
        taskIds.forEach((taskId) => {
            byTask.set(`${normalizeIdentity(benchId)}::${normalizeIdentity(taskId)}`, record);
            if (!benchId) {
                byTask.set(`::${normalizeIdentity(taskId)}`, record);
            }
        });
    });
    return byTask;
}

function assetShardDefinition(payload, benchId) {
    const byBench = payload?.record_shards?.by_bench;
    if (!byBench || typeof byBench !== "object") {
        return null;
    }
    return byBench[benchId] || byBench[normalizeIdentity(benchId)] || null;
}

function assetShardUrlsForTask(payload, benchId, taskId) {
    const definition = assetShardDefinition(payload, benchId);
    if (!definition || typeof definition !== "object") {
        return [];
    }
    return uniqueStrings([
        definition.common_url,
        definition.tasks?.[taskId],
        definition.tasks?.[normalizeIdentity(taskId)],
    ]).filter((url) => isLocalUrl(url));
}

function assetIndexBenchCount(payload, benchId, loadedByBench) {
    const count = Number(payload?.summary?.bench_counts?.[benchId]);
    if (Number.isFinite(count) && count >= 0) {
        return count;
    }
    return loadedByBench.get(benchId)?.length || 0;
}

function assetIndexBenchIds(payload, loadedByBench) {
    const ids = new Set(loadedByBench.keys());
    Object.entries(payload?.summary?.bench_counts || {}).forEach(([benchId, count]) => {
        if (Number(count) > 0) {
            ids.add(benchId);
        }
    });
    Object.keys(payload?.record_shards?.by_bench || {}).forEach((benchId) => ids.add(benchId));
    return ids;
}

function mergeIndexedAssetPayload(target, payload) {
    const incoming = indexAssetRecords(payload);
    incoming.forEach((records, benchId) => {
        const merged = new Map(
            asArray(target.get(benchId)).map((record) => [indexedRecordKey(record), record]),
        );
        records.forEach((record) => merged.set(indexedRecordKey(record), record));
        target.set(benchId, [...merged.values()]);
    });
}

function mergeIndexedVerifierPayload(payload) {
    indexVerifierSources(payload).forEach((record, key) => {
        state.verifierSourcesByTask.set(key, record);
    });
}

async function loadAssetShard(url, kind) {
    const resolved = new URL(url, document.baseURI).href;
    if (state.loadedAssetShardUrls.has(resolved)) {
        return;
    }
    if (!state.assetShardPromises.has(resolved)) {
        const promise = fetchJson(resolved).then((payload) => {
            if (kind === "mirror") {
                mergeIndexedAssetPayload(state.mirrorRecordsByBench, payload);
            }
            else if (kind === "preview") {
                mergeIndexedAssetPayload(state.previewRecordsByBench, payload);
            }
            else {
                mergeIndexedVerifierPayload(payload);
            }
            state.loadedAssetShardUrls.add(resolved);
        }).finally(() => {
            state.assetShardPromises.delete(resolved);
        });
        state.assetShardPromises.set(resolved, promise);
    }
    await state.assetShardPromises.get(resolved);
}

function pendingAssetShardRequests(benchId, taskId) {
    const sources = [
        [state.mirrorIndex, "mirror"],
        [state.previewIndex, "preview"],
        [state.verifierSourceIndex, "verifier"],
    ];
    return sources.flatMap(([payload, kind]) => {
        return assetShardUrlsForTask(payload, benchId, taskId).map((url) => ({url, kind}));
    }).filter(({url}) => {
        const resolved = new URL(url, document.baseURI).href;
        return !state.loadedAssetShardUrls.has(resolved);
    });
}

async function ensureAssetIndexesForTask(benchId, taskId) {
    const requests = pendingAssetShardRequests(benchId, taskId);
    await Promise.all(requests.map(({url, kind}) => loadAssetShard(url, kind)));
}

function normalizeCatalog(payload, sourceUrl) {
    const rawBenches = asArray(
        payload?.benchmarks || payload?.benches || payload?.catalog?.benchmarks || payload?.items,
    );
    const embeddedBenches = new Map();
    const benches = rawBenches
        .map((raw, index) => normalizeBenchEntry(raw, index, sourceUrl))
        .filter((bench) => bench.id);

    rawBenches.forEach((raw, index) => {
        const normalized = benches.find((bench) => bench.sourceIndex === index);
        if (normalized && extractTasks(raw).length) {
            embeddedBenches.set(normalized.id, raw);
        }
    });

    benches.sort((a, b) => {
        if (a.influenceTier !== b.influenceTier) {
            return a.influenceTier - b.influenceTier;
        }
        return a.rank - b.rank;
    });
    return {raw: payload, benches, embeddedBenches};
}

function normalizeBenchEntry(raw, index, sourceUrl) {
    const id = String(raw?.id || raw?.benchmark_id || raw?.slug || "").trim();
    const stats = raw?.stats || {};
    const coverage = raw?.coverage || {};
    const coverageAudit = raw?.coverage_audit || raw?.coverageAudit || {};
    const rawTasks = extractTasks(raw);
    const trackedTasks = firstNumber(
        raw?.task_count,
        stats.tracked_rows,
        coverage.tracked_rows,
        coverageAudit.dashboard_display_count,
        rawTasks.length,
        stats.tracked_tasks,
        coverage.tracked_tasks,
    );
    const officialTasks = firstNumber(
        coverageAudit.official_scope?.headline_total,
        coverage.public_tasks,
        coverage.release_tasks,
        stats.release_tasks,
        trackedTasks,
    );
    const influenceTier = clampNumber(
        firstNumber(raw?.influence_tier, raw?.influenceTier, raw?.rank_tier, inferInfluenceTier(raw)),
        1,
        4,
    );
    const outputFormats = uniqueStrings([
        ...asArray(raw?.output_formats),
        ...rawTasks.flatMap((task) => asArray(task?.output_formats)),
    ]);
    const deliverables = normalizeDeliverables([
        ...asArray(raw?.deliverable_types),
        ...outputFormats,
        ...rawTasks.flatMap((task) => asArray(task?.deliverable_types)),
    ]);
    const dataUrl = firstString(raw?.data_url, raw?.shard_url, raw?.details_url, raw?.path)
        || `data/benches/${encodeURIComponent(id)}.json`;
    return {
        id,
        sourceIndex: index,
        rank: firstNumber(raw?.rank, index + 1),
        name: firstString(raw?.display_name, raw?.name, raw?.short_name, id),
        shortName: firstString(raw?.short_name, raw?.display_name, raw?.name, id),
        summary: firstString(raw?.summary, raw?.description),
        role: firstString(raw?.role),
        relevance: firstString(raw?.relevance, inferRelevance(raw)),
        influence: firstString(raw?.influence, INFLUENCE_GROUPS[influenceTier - 1]?.shortTitle),
        influenceTier,
        influenceBasis: firstString(raw?.influence_basis, raw?.adoption_status),
        adoptionStatus: firstString(raw?.adoption_status),
        tags: uniqueStrings(asArray(raw?.tags)),
        outputFormats,
        deliverables,
        trackedTasks,
        officialTasks,
        coverage,
        coverageAudit,
        catalogScope: raw?.catalog_scope || raw?.catalogScope || {},
        repository: firstString(raw?.repository, raw?.homepage, raw?.url),
        references: asArray(raw?.references || raw?.source_refs),
        license: firstString(raw?.license, raw?.license_note),
        revision: firstString(raw?.revision, raw?.dataset_revision, raw?.release_version),
        dataUrl: resolveCandidateUrl(dataUrl, sourceUrl),
        mirrorManifest: raw?.mirror_manifest || raw?.preview_manifest || null,
        mirrorStatus: firstString(raw?.mirror_status, raw?.preview_status),
        mirrorNotice: firstString(raw?.mirror_notice),
        raw,
    };
}

function renderBenchSidebar() {
    const fragment = document.createDocumentFragment();
    const matching = state.benches.filter(benchMatchesSidebarFilters);

    INFLUENCE_GROUPS.forEach((group) => {
        const benches = matching.filter((bench) => bench.influenceTier === group.tier);
        if (!benches.length) {
            return;
        }
        const section = createElement("section", "bench-group");
        section.dataset.tier = String(group.tier);
        const head = createElement("div", "bench-group-head");
        head.append(
            createElement("span", "bench-group-index", String(group.tier).padStart(2, "0")),
            createElement("strong", "", group.title),
            createElement("small", "", `${benches.length}`),
        );
        const list = createElement("div", "bench-button-list");
        benches.forEach((bench) => list.append(createBenchButton(bench)));
        section.append(head, list);
        fragment.append(section);
    });

    if (!matching.length) {
        fragment.append(createElement("div", "sidebar-empty", "没有符合筛选条件的 Benchmark。"));
    }
    const scrollTop = dom.benchGroups.scrollTop;
    dom.benchGroups.replaceChildren(fragment);
    dom.benchGroups.scrollTop = scrollTop;
}

function createBenchButton(bench) {
    const button = dom.benchButtonTemplate.content.firstElementChild.cloneNode(true);
    button.dataset.benchId = bench.id;
    button.classList.toggle("active", bench.id === state.activeBenchId);
    button.setAttribute("aria-current", bench.id === state.activeBenchId ? "page" : "false");
    const main = button.querySelector(".bench-button-main");
    main.querySelector("strong").textContent = bench.shortName;
    main.querySelector("small").textContent = `${bench.relevance || "待分类"} · ${bench.influence || "待观察"}`;
    const meta = button.querySelector(".bench-button-meta");
    const isOfficeQa = bench.id === "officeqa";
    const officeQaCounts = isOfficeQa ? getOfficeQaCounts(bench) : null;
    meta.append(
        createElement(
            "span",
            "count-badge",
            isOfficeQa
                ? `${formatNumber(officeQaCounts.questionCount)}题`
                : formatNumber(bench.trackedTasks),
        ),
        createElement(
            "span",
            "micro-badge",
            isOfficeQa
                ? `+${formatNumber(officeQaCounts.protocolCount)}协议`
                : bench.deliverables.map(deliverableLabel).slice(0, 2).join(" · ") || "协议",
        ),
    );
    button.addEventListener("click", () => selectBench(bench.id));
    return button;
}

function getOfficeQaCounts(bench) {
    const taskViews = asArray(bench?.taskViews);
    const variants = asArray(bench?.raw?.catalog_scope?.variants);
    const variantCount = (variantId) => {
        if (taskViews.length) {
            return taskViews.filter((task) => {
                return task.unitKind === "question" && task.variantId === variantId;
            }).length;
        }
        const declared = variants.find((variant) => variant?.id === variantId);
        return firstNumber(declared?.question_count);
    };
    const fullCount = variantCount("full");
    const proOriginalCount = taskViews.length
        ? taskViews.filter((task) => {
            return task.unitKind === "question"
                && task.variantId === "full"
                && task.difficulty.toLocaleLowerCase() === "hard";
        }).length
        : firstNumber(bench?.raw?.stats?.original_pro_questions, 133);
    const proV2Count = variantCount("pro_v2");
    const questionCount = taskViews.length
        ? taskViews.filter((task) => task.unitKind === "question").length
        : firstNumber(
            bench?.raw?.stats?.tracked_questions,
            bench?.raw?.coverage?.authorized_questions,
            bench?.raw?.catalog_scope?.authorized_question_count,
            fullCount + proV2Count,
        );
    const protocolCount = taskViews.length
        ? taskViews.filter((task) => task.unitKind === "experiment_mode").length
        : firstNumber(
            bench?.raw?.stats?.protocol_units,
            bench?.raw?.coverage?.protocol_units,
            bench?.raw?.catalog_scope?.experiment_mode_count,
        );
    return {questionCount, protocolCount, fullCount, proOriginalCount, proV2Count};
}

function benchMatchesSidebarFilters(bench) {
    if (state.relevanceFilter && bench.relevance !== state.relevanceFilter) {
        return false;
    }
    if (state.deliverableFilter && !bench.deliverables.includes(state.deliverableFilter)) {
        return false;
    }
    if (!state.benchSearch) {
        return true;
    }
    const haystack = [
        bench.name, bench.shortName, bench.summary, bench.role, bench.relevance,
        bench.influence, ...bench.tags, ...bench.outputFormats,
    ].join(" ").toLocaleLowerCase();
    return haystack.includes(state.benchSearch);
}

function renderCatalogHome() {
    const totalTracked = state.benches.reduce((sum, bench) => sum + bench.trackedTasks, 0);
    const expandable = state.benches.filter((bench) => bench.coverageAudit?.can_expand).length;
    const indexedBenchIds = new Set([
        ...assetIndexBenchIds(state.mirrorIndex, state.mirrorRecordsByBench),
        ...assetIndexBenchIds(state.previewIndex, state.previewRecordsByBench),
    ]);
    const mirrored = state.assetIndexesLoaded
        ? indexedBenchIds.size
        : state.benches.filter((bench) => {
            return bench.raw?.mirror_ready || bench.raw?.preview_ready || bench.raw?.stats?.artifact_ready;
        }).length;
    dom.heroTrackedCount.textContent = `${formatNumber(totalTracked)} tracked units`;
    renderCatalogStats([
        ["收录 Benchmark", formatNumber(state.benches.length), "按外部影响力稳定排序"],
        ["当前跟踪单元", formatNumber(totalTracked), "任务、协议、页面或能力维度"],
        ["可继续扩至全量", formatNumber(expandable), "已有公开数据或明确入口"],
        ["站内镜像覆盖", formatNumber(mirrored), "按实际镜像 / 安全预览索引统计"],
    ]);
    renderTierOverview();
    renderKnowledgeCoverage();
    renderCoverageAudit();
}

function renderCatalogStats(rows) {
    const fragment = document.createDocumentFragment();
    rows.forEach(([label, value, note]) => {
        const card = createElement("article", "catalog-stat-card");
        card.append(
            createElement("span", "", label),
            createElement("strong", "", value),
            createElement("small", "", note),
        );
        fragment.append(card);
    });
    dom.catalogStats.replaceChildren(fragment);
}

function renderTierOverview() {
    const fragment = document.createDocumentFragment();
    INFLUENCE_GROUPS.forEach((group) => {
        const count = state.benches.filter((bench) => bench.influenceTier === group.tier).length;
        const card = createElement("article", "tier-card");
        card.append(
            createElement("span", "tier-card-index", `T${group.tier}`),
            createElement("h3", "", group.title),
            createElement("p", "", group.description),
            createElement("span", "tier-card-count", `${count} Benches`),
        );
        fragment.append(card);
    });
    dom.tierOverview.replaceChildren(fragment);
}

function renderKnowledgeCoverage() {
    const payload = state.knowledgeCoverage;
    if (!payload) {
        const message = state.knowledgeCoverageError
            ? `公开审计读取失败：${state.knowledgeCoverageError}`
            : "正在读取公开审计";
        dom.knowledgeCoverageStatus.textContent = message;
        dom.knowledgeCoverageStats.replaceChildren();
        dom.coverageCollisionGrid.replaceChildren();
        dom.knowledgeCoverageTableBody.replaceChildren();
        dom.knowledgeCoverageCards.replaceChildren();
        return;
    }

    const items = asArray(payload.items).slice().sort((left, right) => {
        return firstNumber(left?.order, 999) - firstNumber(right?.order, 999);
    });
    const rows = items.map((item) => ({
        item,
        indexed: getCoverageIndexedCount(item),
        denominator: Math.max(0, firstNumber(item?.public_scope?.denominator, 0)),
    }));
    const completed = rows.filter((row) => {
        return row.denominator > 0 && row.indexed >= row.denominator;
    }).length;
    const indexedTotal = rows.reduce((sum, row) => sum + row.indexed, 0);
    const publicTotal = rows.reduce((sum, row) => sum + row.denominator, 0);
    const metadataOnly = rows.filter((row) => {
        return COVERAGE_STATUS_META[row.item.status]?.group === "metadata";
    }).length;
    const excluded = rows.filter((row) => {
        return COVERAGE_STATUS_META[row.item.status]?.group === "excluded";
    }).length;

    dom.knowledgeCoverageStatus.textContent = `${items.length} 项 · ${completed} 项公开范围已齐`;
    renderKnowledgeCoverageStats([
        ["知识库清单", `${items.length} / 22`, "逐项保留 family 身份"],
        ["站内镜像 / 可索引公开", `${formatNumber(indexedTotal)} / ${formatNumber(publicTotal)}`, "由当前 catalog 实时汇总"],
        ["仅元数据", formatNumber(metadataOnly), "Gated 或未声明许可"],
        ["排除 / 待发布", formatNumber(excluded), "不生成虚假任务卡"],
    ]);

    const collisionFragment = document.createDocumentFragment();
    asArray(payload.collision_boundaries).forEach((boundary) => {
        const card = createElement("article", "coverage-collision-card");
        card.append(
            createElement("span", "", "IDENTITY BOUNDARY"),
            createElement("strong", "", boundary.title || boundary.key || "名称边界"),
            createElement("p", "", boundary.note || ""),
        );
        collisionFragment.append(card);
    });
    dom.coverageCollisionGrid.replaceChildren(collisionFragment);

    const tableFragment = document.createDocumentFragment();
    const cardFragment = document.createDocumentFragment();
    rows.forEach((row) => {
        tableFragment.append(createKnowledgeCoverageRow(row));
        cardFragment.append(createKnowledgeCoverageCard(row));
    });
    dom.knowledgeCoverageTableBody.replaceChildren(tableFragment);
    dom.knowledgeCoverageCards.replaceChildren(cardFragment);
}

function renderKnowledgeCoverageStats(rows) {
    const fragment = document.createDocumentFragment();
    rows.forEach(([label, value, note]) => {
        const card = createElement("article", "kb-coverage-stat");
        card.append(
            createElement("span", "", label),
            createElement("strong", "", value),
            createElement("small", "", note),
        );
        fragment.append(card);
    });
    dom.knowledgeCoverageStats.replaceChildren(fragment);
}

function getCoverageIndexedCount(item) {
    const liveIds = new Set(uniqueStrings(asArray(item?.live_benchmark_ids)));
    const count = state.benches.reduce((sum, bench) => {
        return liveIds.has(bench.id) ? sum + Math.max(0, bench.trackedTasks) : sum;
    }, 0);
    const denominator = Math.max(0, firstNumber(item?.public_scope?.denominator, 0));
    return item?.public_scope?.count_cap && denominator > 0 ? Math.min(count, denominator) : count;
}

function getCoverageStatusMeta(item, indexed, denominator) {
    const meta = COVERAGE_STATUS_META[item?.status] || {
        label: item?.status || "待核验",
        group: "unknown",
    };
    const incomplete = meta.group === "public" && denominator > 0 && indexed < denominator;
    return {
        ...meta,
        label: incomplete && meta.incompleteLabel ? meta.incompleteLabel : meta.label,
    };
}

function createCoverageStatusBadge(item, indexed, denominator) {
    const stack = createElement("span", "kb-coverage-status-stack");
    const statuses = uniqueStrings([item?.status, ...asArray(item?.secondary_statuses)]);
    statuses.forEach((status) => {
        const meta = getCoverageStatusMeta({...item, status}, indexed, denominator);
        const badge = createElement(
            "span",
            `kb-coverage-status kb-coverage-status-${meta.group}`,
            meta.label,
        );
        badge.title = status;
        stack.append(badge);
    });
    return stack;
}

function createCoverageProgress(item, indexed, denominator) {
    const scope = item?.public_scope || {};
    const container = createElement("div", "kb-coverage-progress");
    const value = denominator > 0
        ? `${formatNumber(indexed)} / ${formatNumber(denominator)}`
        : "0 个可运行公开任务";
    const head = document.createElement("div");
    head.append(
        createElement("strong", "", value),
        createElement("span", "", scope.unit || "tasks"),
    );
    const track = createElement("span", "kb-coverage-progress-track");
    const bar = document.createElement("i");
    const percentage = denominator > 0 ? Math.min(100, (indexed / denominator) * 100) : 0;
    bar.style.width = `${percentage}%`;
    track.append(bar);
    container.append(
        head,
        track,
        createElement("small", "", scope.official_scale || "以官方发布口径为准"),
    );
    return container;
}

function createCoverageOfficialLinks(item) {
    const container = createElement("div", "kb-coverage-links");
    asArray(item?.official_links).forEach((source) => {
        const url = safeHttpUrl(source?.url);
        if (!url) {
            return;
        }
        const link = createElement("a", "", `${source.label || "官方来源"} ↗`);
        link.href = url;
        link.target = "_blank";
        link.rel = "noreferrer noopener";
        container.append(link);
    });
    return container;
}

function createKnowledgeCoverageRow({item, indexed, denominator}) {
    const row = document.createElement("tr");
    const nameCell = document.createElement("td");
    const familyMembers = uniqueStrings(asArray(item?.family_members));
    nameCell.append(
        createElement(
            "strong",
            "kb-coverage-name",
            `${String(firstNumber(item?.order, 0)).padStart(2, "0")} · ${item.requested_name || "Unnamed"}`,
        ),
        createElement("code", "kb-coverage-family-id", item?.canonical_family_id || ""),
    );
    if (familyMembers.length > 1) {
        nameCell.append(createElement("small", "", familyMembers.join(" · ")));
    }

    const statusCell = document.createElement("td");
    statusCell.append(createCoverageStatusBadge(item, indexed, denominator));

    const countCell = document.createElement("td");
    countCell.append(createCoverageProgress(item, indexed, denominator));

    const accessCell = createElement("td", "", item?.access_license || "许可待核验");
    const reasonCell = document.createElement("td");
    reasonCell.append(
        createElement("p", "kb-coverage-reason", item?.coverage_reason || ""),
        createElement("p", "kb-coverage-next", `下一步：${item?.next_action || "持续跟踪官方发布。"}`),
    );
    const sourceCell = document.createElement("td");
    sourceCell.append(createCoverageOfficialLinks(item));
    row.append(nameCell, statusCell, countCell, accessCell, reasonCell, sourceCell);
    return row;
}

function createKnowledgeCoverageCard({item, indexed, denominator}) {
    const card = createElement("article", "kb-coverage-card");
    const head = createElement("div", "kb-coverage-card-head");
    const title = document.createElement("div");
    title.append(
        createElement(
            "strong",
            "",
            `${String(firstNumber(item?.order, 0)).padStart(2, "0")} · ${item.requested_name || "Unnamed"}`,
        ),
        createElement("code", "", item?.canonical_family_id || ""),
    );
    head.append(title, createCoverageStatusBadge(item, indexed, denominator));
    const facts = createElement("dl", "kb-coverage-card-facts");
    facts.append(
        createElement("dt", "", "许可 / 访问"),
        createElement("dd", "", item?.access_license || "待核验"),
        createElement("dt", "", "处置原因"),
        createElement("dd", "", item?.coverage_reason || ""),
        createElement("dt", "", "下一步"),
        createElement("dd", "", item?.next_action || "持续跟踪官方发布。"),
    );
    card.append(
        head,
        createCoverageProgress(item, indexed, denominator),
        facts,
        createCoverageOfficialLinks(item),
    );
    return card;
}

function renderCoverageAudit() {
    const audits = state.benches.filter((bench) => {
        return bench.trackedTasks < 10 && Object.keys(bench.coverageAudit || {}).length;
    });
    const causeCounts = new Map();
    audits.forEach((bench) => {
        const cause = inferCoverageCause(bench);
        causeCounts.set(cause, (causeCounts.get(cause) || 0) + 1);
    });
    const summaryRows = [
        ["看板主动抽样", causeCounts.get("dashboard_sampling") || 0, "公开数据可继续扩充"],
        ["公开子集 / gated", causeCounts.get("public_limited") || 0, "受许可、申请或防污染设计限制"],
        ["统计单位不同", causeCounts.get("unit_mismatch") || 0, "行代表协议、页面或能力维度"],
    ];
    const summaryFragment = document.createDocumentFragment();
    summaryRows.filter(([_label, count]) => count > 0).forEach(([label, count, note]) => {
        const card = createElement("article", "audit-summary-card");
        card.append(
            createElement("strong", "", `${label} · ${count}`),
            createElement("span", "", note),
        );
        summaryFragment.append(card);
    });
    dom.auditSummary.replaceChildren(summaryFragment);

    const tableFragment = document.createDocumentFragment();
    audits.forEach((bench) => tableFragment.append(createAuditRow(bench)));
    dom.auditTableBody.replaceChildren(tableFragment);
}

function createAuditRow(bench) {
    const audit = bench.coverageAudit;
    const row = document.createElement("tr");
    const benchCell = document.createElement("td");
    benchCell.append(createElement("strong", "", bench.shortName));
    const source = asArray(audit.sources)[0];
    if (source?.url && safeHttpUrl(source.url)) {
        const link = createElement("a", "", source.label || "官方证据 ↗");
        link.href = source.url;
        link.target = "_blank";
        link.rel = "noreferrer noopener";
        benchCell.append(link);
    }

    const scope = audit.official_scope || {};
    const scopeCell = document.createElement("td");
    scopeCell.append(
        createElement("strong", "", `${formatNumber(scope.headline_total || bench.officialTasks)} ${scope.unit || "units"}`),
        createElement("span", "", scope.breakdown || "以官方发布口径为准。"),
    );

    const accessCell = document.createElement("td");
    accessCell.append(
        createElement("span", "audit-access-badge", audit.access_class || "待核验"),
        createElement("div", "", audit.public_extent || "公开范围待进一步核验。"),
    );
    const reasonCell = createElement("td", "", audit.why_dashboard_is_small || "目录当前保留代表性拆解。 ");
    const expansionCell = document.createElement("td");
    expansionCell.append(
        createElement("strong", "", audit.can_expand ? "可扩" : "受限"),
        createElement("span", "", audit.expansion_ceiling || audit.recommendation || "以官方许可为边界。"),
    );
    row.append(benchCell, scopeCell, accessCell, reasonCell, expansionCell);
    return row;
}

async function selectBench(benchId, options = {}) {
    const entry = state.benches.find((bench) => bench.id === benchId);
    if (!entry) {
        return;
    }
    setSidebarOpen(false);
    state.activeBenchId = benchId;
    markActiveBenchButton();

    if (state.loadedBenches.has(benchId)) {
        activateLoadedBench(
            state.loadedBenches.get(benchId),
            options.taskId || "",
            options.variant || "",
        );
        return;
    }

    abortActiveFetch();
    state.fetchController = new AbortController();
    const retry = () => selectBench(benchId, options);
    state.retryAction = retry;
    showLoader({
        kicker: "BENCH SHARD · STAGE 2 / 2",
        title: `正在展开 ${entry.shortName}`,
        message: "题量再大也没关系：数据读取完成后会按批渲染。",
    });
    setNavStatus("loading", `加载 ${entry.shortName}`);

    let payload = null;
    let payloadSourceUrl = entry.dataUrl;
    try {
        payload = await fetchJsonWithProgress(entry.dataUrl, (progress) => {
            updateLoaderProgress(progress, `${entry.shortName} 题库`);
        }, state.fetchController.signal);
    }
    catch (error) {
        if (error.name === "AbortError") {
            return;
        }
        const embedded = state.embeddedBenches.get(benchId);
        if (embedded) {
            payload = embedded;
            payloadSourceUrl = state.catalogUrl;
            updateLoader({
                message: "独立分片尚未生成，暂时使用兼容清单中的内嵌题库。",
                percent: 92,
            });
        }
        else {
            setNavStatus("error", `${entry.shortName} 加载失败`);
            showLoaderError("题库没有加载成功", error.message, retry);
            return;
        }
    }

    try {
        updateLoader({message: "正在建立搜索索引与预览映射…", percent: 96});
        const loaded = await normalizeLoadedBench(payload, entry, payloadSourceUrl);
        state.loadedBenches.set(benchId, loaded);
        activateLoadedBench(loaded, options.taskId || "", options.variant || "");
        hideLoader();
        const officeQaCounts = loaded.id === "officeqa" ? getOfficeQaCounts(loaded) : null;
        setNavStatus(
            "ready",
            loaded.id === "officeqa"
                ? `${formatNumber(officeQaCounts.questionCount)} 题 · `
                    + `${formatNumber(officeQaCounts.protocolCount)} 协议`
                : `${formatNumber(loaded.tasks.length)} 个单元`,
        );
    }
    catch (error) {
        setNavStatus("error", `${entry.shortName} 解析失败`);
        showLoaderError("题库格式无法识别", error.message, retry);
    }
}

async function normalizeLoadedBench(payload, entry, payloadSourceUrl) {
    const rawBench = payload?.benchmark || payload?.bench || payload?.metadata || payload;
    const mergedRaw = {...entry.raw, ...(rawBench || {})};
    const tasks = extractTasks(payload).length ? extractTasks(payload) : extractTasks(rawBench);
    const normalizedEntry = normalizeBenchEntry(mergedRaw, entry.sourceIndex, state.catalogUrl);
    const taskViews = tasks.map((task, index) => createTaskView(task, index));
    const mirrorDeclaration = payload?.mirror_manifest || payload?.preview_manifest
        || rawBench?.mirror_manifest || entry.mirrorManifest;
    let mirrorManifest = typeof mirrorDeclaration === "object" ? mirrorDeclaration : null;
    if (typeof mirrorDeclaration === "string" && isLocalUrl(mirrorDeclaration)) {
        try {
            mirrorManifest = await fetchJson(resolveCandidateUrl(mirrorDeclaration, entry.dataUrl));
        }
        catch (_error) {
            mirrorManifest = null;
        }
    }
    const loaded = {
        ...normalizedEntry,
        tasks,
        taskViews,
        raw: mergedRaw,
        payload,
        assetBaseUrl: payloadSourceUrl,
        mirrorManifest,
    };
    applyMirrorPlan(loaded);
    return loaded;
}

function activateLoadedBench(bench, requestedTaskId, requestedVariant) {
    state.activeBench = bench;
    state.activeBenchId = bench.id;
    state.activeTaskId = "";
    state.taskViews = bench.taskViews;
    state.benchMirrorManifest = bench.mirrorManifest;
    resetTaskFilters();
    const requested = requestedTaskId
        ? bench.taskViews.find((task) => task.id === requestedTaskId)
        : null;
    if (bench.id === "officeqa") {
        state.taskVariant = officeQaVariantForTask(requested)
            || normalizeOfficeQaVariant(requestedVariant)
            || "questions";
    }
    renderBenchHero(bench);
    renderBenchAudit(bench);
    populateTaskFilters();
    filterAndRenderTasks();
    dom.catalogHome.classList.add("hidden");
    dom.fatalState.classList.add("hidden");
    dom.benchWorkspace.classList.remove("hidden");
    markActiveBenchButton();

    const first = requested && taskMatchesActiveVariant(requested)
        ? requested
        : state.filteredTasks[0];
    if (first) {
        selectTask(first.id, {updateLocation: false, scroll: false});
    }
    else {
        renderEmptyInspector("这个 Bench 没有可公开展示的任务行。", "仍可查看上方的协议与开放性说明。");
    }
    updateLocation(bench.id, first?.id || "", state.taskVariant);
}

function renderBenchHero(bench) {
    const top = createElement("div", "bench-hero-top");
    const copy = document.createElement("div");
    copy.append(
        createElement("span", "bench-rank", `EXTERNAL INFLUENCE · TIER ${bench.influenceTier}`),
        createElement("h1", "", bench.name),
        createElement("p", "bench-summary", bench.summary || "该 Bench 的任务、输入、Verifier 与交付物预览。"),
    );
    const actions = createElement("div", "bench-hero-actions");
    const catalogButton = createElement("button", "bench-hero-link", "目录首页");
    catalogButton.type = "button";
    catalogButton.addEventListener("click", showCatalogHome);
    actions.append(catalogButton);
    if (bench.repository && safeHttpUrl(bench.repository)) {
        actions.append(createExternalLink("官方入口 ↗", bench.repository, "bench-hero-link"));
    }
    top.append(copy, actions);

    const badges = createElement("div", "bench-badges");
    badges.append(
        createElement("span", "axis-badge relevance", `相关性 · ${bench.relevance || "待分类"}`),
        createElement("span", "axis-badge influence", `影响力 · ${bench.influence || "待观察"}`),
    );
    bench.deliverables.slice(0, 7).forEach((type) => {
        badges.append(createElement("span", "format-badge", deliverableLabel(type)));
    });

    const metrics = createElement("div", "bench-metrics");
    const audit = bench.coverageAudit || {};
    const scope = audit.official_scope || {};
    const indexedMirrorCount = assetIndexBenchCount(
        state.mirrorIndex,
        bench.id,
        state.mirrorRecordsByBench,
    );
    const indexedPreviewCount = assetIndexBenchCount(
        state.previewIndex,
        bench.id,
        state.previewRecordsByBench,
    );
    const mirrorMetric = indexedMirrorCount || indexedPreviewCount
        ? `${formatNumber(indexedMirrorCount)} 镜像 · ${formatNumber(indexedPreviewCount)} 可预览`
        : mirrorStatusLabel(bench.mirrorStatus) || "等待站内镜像索引";
    const officeQaCounts = bench.id === "officeqa" ? getOfficeQaCounts(bench) : null;
    const rows = bench.id === "officeqa"
        ? [
            [
                "当前题库",
                `${formatNumber(officeQaCounts.questionCount)} 题 · `
                    + `${formatNumber(officeQaCounts.protocolCount)} 协议`,
            ],
            [
                "版本",
                `Full ${formatNumber(officeQaCounts.fullCount)}（含原 Pro `
                    + `${formatNumber(officeQaCounts.proOriginalCount)}） · `
                    + `Pro V2 ${formatNumber(officeQaCounts.proV2Count)}`,
            ],
            ["数据许可", bench.license || audit.access_class || "待核验"],
            ["镜像状态", mirrorMetric],
        ]
        : [
            ["当前题库", `${formatNumber(bench.tasks.length)} rows`],
            ["官方规模", `${formatNumber(scope.headline_total || bench.officialTasks)} ${scope.unit || "units"}`],
            ["数据许可", bench.license || audit.access_class || "待核验"],
            ["镜像状态", mirrorMetric],
        ];
    rows.forEach(([label, value]) => {
        const item = createElement("div", "bench-metric");
        item.title = value;
        item.append(createElement("span", "", label), createElement("strong", "", value));
        metrics.append(item);
    });
    const mirrorStatus = String(bench.mirrorStatus || "").toLocaleLowerCase();
    const licenseReviewPending = mirrorStatus.includes("review") && indexedMirrorCount === 0;
    const licenseAlert = createElement(
        "div",
        `bench-license-alert${licenseReviewPending ? "" : " hidden"}`,
        bench.mirrorNotice
            ? `镜像许可待确认 · ${bench.mirrorNotice}`
            : "镜像许可待确认 · 当前仅展示完整任务元数据与官方入口，未在本站再分发二进制文件。",
    );
    const heroChildren = [top, badges];
    if (bench.id === "officeqa") {
        heroChildren.push(createOfficeQaDataNotice(bench));
    }
    heroChildren.push(licenseAlert, metrics);
    dom.benchHero.replaceChildren(...heroChildren);
}

function createOfficeQaDataNotice(bench) {
    const revisions = new Map();
    asArray(bench.taskViews).forEach((task) => {
        if (!task.variantId || task.variantId === "protocol" || !task.datasetRevision) {
            return;
        }
        revisions.set(task.variantId, task.datasetRevision);
    });
    const fullRevision = revisions.get("full") || "revision pending";
    const v2Revision = revisions.get("pro_v2") || "revision pending";
    const notice = createElement("aside", "officeqa-data-notice");
    const copy = document.createElement("div");
    copy.append(
        createElement("strong", "", "授权数据 · 可公开问题可审阅，答案已排除"),
        createElement(
            "p",
            "",
            "本站不会代用户访问受门禁保护的数据；Gold answer、答案哈希"
                + "与 oracle 页码均未进入题库 shard、搜索索引"
                + "或 Verifier 配置。",
        ),
    );
    const revision = createElement("div", "officeqa-revision-stack");
    revision.append(
        createElement("span", "", `FULL · ${shortRevision(fullRevision)}`),
        createElement("span", "", `PRO V2 · ${shortRevision(v2Revision)}`),
    );
    notice.append(createElement("span", "officeqa-lock-mark", "GATED"), copy, revision);
    return notice;
}

function shortRevision(value) {
    const revision = String(value || "").trim();
    return revision.length > 12 ? revision.slice(0, 12) : revision;
}

function renderBenchAudit(bench) {
    const audit = bench.coverageAudit || {};
    const hasAudit = Object.keys(audit).length > 0;
    dom.benchAuditCard.classList.toggle("hidden", !hasAudit);
    if (!hasAudit) {
        return;
    }
    dom.benchAuditCaption.textContent = audit.access_class || "收录口径";
    const rows = [
        ["公开边界", audit.public_extent || "以官方仓库与许可为准。"],
        ["为什么当前是这些行", audit.why_dashboard_is_small || "当前按公开可审计单元展示。"],
        ["下一步扩展", audit.recommendation || audit.expansion_ceiling || "持续跟随官方 release。"],
    ];
    if (bench.mirrorNotice) {
        rows.push(["镜像边界", bench.mirrorNotice]);
    }
    const fragment = document.createDocumentFragment();
    rows.forEach(([label, text]) => {
        const card = createElement("div", "audit-detail-card");
        card.append(createElement("span", "", label), createElement("p", "", text));
        fragment.append(card);
    });
    dom.benchAuditBody.replaceChildren(fragment);
}

function createTaskView(raw, index) {
    const id = String(raw?.id || raw?.task_id || raw?.uid || raw?.slug || index + 1);
    const unitKind = firstString(raw?.unit_kind, "task");
    const variantId = firstString(raw?.variant_id);
    const variantLabel = firstString(raw?.variant_label);
    const titleOriginal = firstString(raw?.title, raw?.name, raw?.instruction, `Task ${index + 1}`);
    const category = firstString(raw?.category, raw?.domain, raw?.task_type, "未分类");
    const prompt = firstString(
        raw?.task_prompt,
        raw?.prompt,
        raw?.instruction,
        raw?.question,
        raw?.prompt_excerpt,
    );
    const nativeChinese = /^zh(?:-|$)/i.test(firstString(raw?.original_language))
        || /^(?:not_required_native_zh|native_zh)$/i.test(
            firstString(raw?.translation_status, raw?.task_prompt_zh_status),
        );
    const promptTranslation = extractExactPromptTranslation(raw);
    const titleTranslation = extractExactTitleTranslation(raw);
    const translatedTitle = firstString(
        titleTranslation.text,
        promptTranslation.text ? firstSentence(promptTranslation.text, 90) : "",
    );
    const title = !isPrimarilyChinese(titleOriginal) && translatedTitle ? translatedTitle : titleOriginal;
    const promptZh = promptTranslation.text;
    const outputFormats = uniqueStrings(asArray(raw?.output_formats));
    const deliverables = normalizeDeliverables([
        ...asArray(raw?.deliverable_types),
        ...outputFormats,
        raw?.artifact?.kind,
        raw?.artifact?.filename ? fileExtension(raw.artifact.filename) : "",
    ]);
    const searchText = [
        id, title, titleOriginal, category, prompt, promptZh, raw?.task_prompt_zh,
        raw?.prompt_excerpt, raw?.prompt_zh_excerpt,
        raw?.difficulty, raw?.status, unitKind, variantId, variantLabel,
        raw?.dataset_revision, raw?.metadata?.question_uid,
        ...asArray(raw?.gold_provenance?.files).map((file) => firstString(file?.filename, file)),
        ...deliverables, ...outputFormats,
    ].join(" ").toLocaleLowerCase();
    return {
        id,
        index,
        unitKind,
        variantId,
        variantLabel,
        datasetRevision: firstString(raw?.dataset_revision),
        fetchedAt: firstString(raw?.fetched_at),
        title,
        titleOriginal,
        category,
        difficulty: firstString(raw?.difficulty, raw?.level),
        status: firstString(raw?.status),
        prompt,
        promptZh,
        promptTranslationStatus: promptTranslation.status,
        promptTranslationIsMachine: promptTranslation.isMachine,
        nativeChinese,
        outputFormats,
        deliverables,
        searchText,
        raw,
    };
}

function populateTaskFilters() {
    const categories = uniqueStrings(state.taskViews.map((task) => task.category)).sort(localeSort);
    const deliverables = uniqueStrings(state.taskViews.flatMap((task) => task.deliverables));
    replaceSelectOptions(dom.taskCategoryFilter, "全部类别", categories.map((value) => [value, value]));
    replaceSelectOptions(
        dom.taskDeliverableFilter,
        "全部产物",
        deliverables.map((value) => [value, deliverableLabel(value)]),
    );
    renderTaskVariantFilters();
}

function renderTaskVariantFilters() {
    const isOfficeQa = state.activeBenchId === "officeqa";
    dom.taskVariantRow.classList.toggle("hidden", !isOfficeQa);
    dom.taskVariantFilters.replaceChildren();
    if (!isOfficeQa) {
        return;
    }
    const fragment = document.createDocumentFragment();
    OFFICEQA_VARIANT_OPTIONS.forEach((option) => {
        const count = state.taskViews.filter((task) => {
            if (option.unitKind) {
                return task.unitKind === option.unitKind;
            }
            if (option.id === "pro_original") {
                return task.unitKind === "question"
                    && task.variantId === "full"
                    && task.difficulty.toLocaleLowerCase() === "hard";
            }
            return task.variantId === option.variantId;
        }).length;
        const button = createElement(
            "button",
            `task-variant-button${state.taskVariant === option.id ? " active" : ""}`,
        );
        button.type = "button";
        button.dataset.taskVariant = option.id;
        button.setAttribute("aria-pressed", String(state.taskVariant === option.id));
        button.append(
            createElement("span", "", option.label),
            createElement("strong", "", formatNumber(count)),
        );
        fragment.append(button);
    });
    dom.taskVariantFilters.append(fragment);
}

function normalizeOfficeQaVariant(value) {
    const normalized = String(value || "").trim().toLocaleLowerCase();
    return OFFICEQA_VARIANT_OPTIONS.some((option) => option.id === normalized)
        ? normalized
        : "";
}

function officeQaVariantForTask(task) {
    if (!task) {
        return "";
    }
    if (task.unitKind === "experiment_mode" || task.variantId === "protocol") {
        return "protocol";
    }
    return normalizeOfficeQaVariant(task.variantId);
}

function taskMatchesActiveVariant(task) {
    if (state.activeBenchId !== "officeqa") {
        return true;
    }
    if (state.taskVariant === "protocol") {
        return task.unitKind === "experiment_mode" || task.variantId === "protocol";
    }
    if (state.taskVariant === "pro_original") {
        return task.unitKind === "question"
            && task.variantId === "full"
            && task.difficulty.toLocaleLowerCase() === "hard";
    }
    if (state.taskVariant === "full" || state.taskVariant === "pro_v2") {
        return task.unitKind === "question" && task.variantId === state.taskVariant;
    }
    return task.unitKind === "question";
}

function setTaskVariant(value, options = {}) {
    if (state.activeBenchId !== "officeqa") {
        return;
    }
    const next = normalizeOfficeQaVariant(value) || "questions";
    if (state.taskVariant === next && !options.force) {
        return;
    }
    state.taskVariant = next;
    renderTaskVariantFilters();
    filterAndRenderTasks();
    if (options.updateLocation) {
        updateLocation(state.activeBenchId, state.activeTaskId, state.taskVariant);
    }
}

function officeQaTaskLabel(task) {
    if (task.unitKind === "experiment_mode" || task.variantId === "protocol") {
        return "实验协议";
    }
    if (task.variantId === "pro_v2") {
        return "Pro V2";
    }
    if (task.variantId === "full") {
        return "Full";
    }
    return task.variantLabel || "OfficeQA";
}

function filterAndRenderTasks() {
    state.filteredTasks = state.taskViews.filter((task) => {
        if (!taskMatchesActiveVariant(task)) {
            return false;
        }
        if (state.taskCategory && task.category !== state.taskCategory) {
            return false;
        }
        if (state.taskDeliverable && !task.deliverables.includes(state.taskDeliverable)) {
            return false;
        }
        return !state.taskSearch || task.searchText.includes(state.taskSearch);
    });
    state.renderedTaskCount = 0;
    dom.taskList.replaceChildren();
    renderNextTaskBatch();
    const scopedCount = state.taskViews.filter(taskMatchesActiveVariant).length;
    const allCount = state.taskViews.length;
    if (state.activeBenchId === "officeqa") {
        const unitLabel = state.taskVariant === "protocol" ? "个实验协议" : "道题";
        dom.taskResultSummary.textContent = (
            `显示 ${formatNumber(state.filteredTasks.length)} / ${formatNumber(scopedCount)} ${unitLabel}`
        );
    }
    else {
        dom.taskResultSummary.textContent = (
            `显示 ${formatNumber(state.filteredTasks.length)} / ${formatNumber(allCount)} 个单元`
        );
    }
    dom.renderModeLabel.textContent = scopedCount > TASK_BATCH_SIZE
        ? `每批 ${TASK_BATCH_SIZE} 条 · 滚动继续`
        : "一次渲染完成";
    dom.taskEmptyState.classList.toggle("hidden", state.filteredTasks.length > 0);
    const activeVisible = state.filteredTasks.some((task) => task.id === state.activeTaskId);
    if (!activeVisible && state.filteredTasks[0]) {
        selectTask(state.filteredTasks[0].id, {updateLocation: false, scroll: false});
    }
    else if (!state.filteredTasks.length) {
        renderEmptyInspector("没有匹配的任务", "换一个关键词、类别或交付物筛选。 ");
    }
}

function renderNextTaskBatch() {
    if (state.renderedTaskCount >= state.filteredTasks.length) {
        dom.loadMoreTasks.classList.add("hidden");
        return;
    }
    const next = state.filteredTasks.slice(
        state.renderedTaskCount,
        state.renderedTaskCount + TASK_BATCH_SIZE,
    );
    const fragment = document.createDocumentFragment();
    next.forEach((task) => fragment.append(createTaskCard(task)));
    dom.taskList.append(fragment);
    state.renderedTaskCount += next.length;
    dom.loadMoreTasks.classList.toggle("hidden", state.renderedTaskCount >= state.filteredTasks.length);
}

function createTaskCard(task) {
    const button = createElement("button", "task-card");
    button.type = "button";
    button.dataset.taskId = task.id;
    button.classList.toggle("active", task.id === state.activeTaskId);
    button.setAttribute("aria-current", task.id === state.activeTaskId ? "true" : "false");
    const copy = createElement("span", "task-card-copy");
    const title = createElement("strong", "", task.title);
    if (task.titleOriginal && task.titleOriginal !== task.title) {
        title.title = `英文原题：${task.titleOriginal}`;
    }
    copy.append(
        title,
        createElement("small", "", `${task.category} · ${task.id}`),
    );
    const typeLabel = state.activeBenchId === "officeqa"
        ? officeQaTaskLabel(task)
        : task.deliverables.map(deliverableLabel).slice(0, 2).join(" + ") || "协议";
    button.append(
        createElement("span", "task-number", String(task.index + 1).padStart(2, "0")),
        copy,
        createElement("span", "task-card-type", typeLabel),
    );
    button.addEventListener("click", () => selectTask(task.id, {updateLocation: true, scroll: true}));
    return button;
}

async function selectTask(taskId, options = {}) {
    const task = state.taskViews.find((candidate) => candidate.id === taskId);
    if (!task) {
        return;
    }
    state.activeTaskId = taskId;
    const selectionToken = ++state.assetSelectionToken;
    dom.taskList.querySelectorAll(".task-card").forEach((button) => {
        const active = button.dataset.taskId === taskId;
        button.classList.toggle("active", active);
        button.setAttribute("aria-current", String(active));
    });
    if (options.updateLocation) {
        updateLocation(state.activeBenchId, taskId, state.taskVariant);
    }
    if (options.scroll && window.innerWidth <= 760) {
        dom.taskInspector.scrollIntoView({behavior: "smooth", block: "start"});
    }
    const pending = pendingAssetShardRequests(state.activeBenchId, taskId);
    const needsDetail = Boolean(task.raw?.detail_url && !task.detailLoaded);
    if (pending.length || needsDetail) {
        renderTaskAssetLoading(task, pending.length, needsDetail);
        const [detailResult] = await Promise.allSettled([
            ensureTaskDetail(task),
            ensureAssetIndexesForTask(state.activeBenchId, taskId),
        ]);
        if (detailResult.status === "rejected") {
            if (selectionToken === state.assetSelectionToken
                && taskId === state.activeTaskId) {
                renderTaskDetailFailure(task, detailResult.reason);
            }
            return;
        }
        if (selectionToken !== state.assetSelectionToken
            || taskId !== state.activeTaskId) {
            return;
        }
    }
    renderTaskInspector(task);
}

async function ensureTaskDetail(task) {
    const declaredUrl = firstString(task.raw?.detail_url);
    if (!declaredUrl || task.detailLoaded) {
        return;
    }
    if (!isLocalUrl(declaredUrl)) {
        throw new Error("任务详情必须来自本站分片");
    }
    const resolved = new URL(declaredUrl, document.baseURI).href;
    if (!state.taskDetailPromises.has(resolved)) {
        state.taskDetailPromises.set(resolved, fetchJson(resolved).finally(() => {
            state.taskDetailPromises.delete(resolved);
        }));
    }
    const payload = await state.taskDetailPromises.get(resolved);
    const rawTask = payload?.task || payload?.record || payload;
    const detailId = firstString(rawTask?.id, rawTask?.task_id, rawTask?.uid, rawTask?.slug);
    if (!rawTask || typeof rawTask !== "object" || detailId !== task.id) {
        throw new Error("任务详情分片与目录 ID 不一致");
    }
    const fullView = createTaskView(rawTask, task.index);
    Object.assign(task, fullView, {detailLoaded: true});
}

function renderTaskAssetLoading(task, shardCount, needsDetail) {
    const placeholder = createElement("div", "inspector-placeholder");
    placeholder.setAttribute("aria-busy", "true");
    const work = shardCount + (needsDetail ? 1 : 0);
    placeholder.append(
        createElement("span", "placeholder-mark", "INDEX"),
        createElement("h3", "", `正在读取 ${task.title}`),
        createElement(
            "p",
            "",
            `只加载这道题关联的 ${formatNumber(work)} 个详情、镜像、预览与 Verifier 分片。`,
        ),
    );
    dom.taskInspector.replaceChildren(placeholder);
}

function renderTaskDetailFailure(task, error) {
    const placeholder = createElement("div", "inspector-placeholder");
    const retry = createElement("button", "external-link-button", "重新读取这道题");
    retry.type = "button";
    retry.addEventListener("click", () => {
        void selectTask(task.id, {updateLocation: false, scroll: false});
    });
    placeholder.append(
        createElement("span", "placeholder-mark", "RETRY"),
        createElement("h3", "", "任务详情没有加载成功"),
        createElement("p", "", firstString(error?.message, "请稍后重试。")),
        retry,
    );
    dom.taskInspector.replaceChildren(placeholder);
}

function renderTaskInspector(task) {
    if (!task) {
        return;
    }
    const raw = task.raw;
    const header = createElement("header", "inspector-head");
    const kicker = createElement("div", "inspector-kicker-row");
    kicker.append(
        createElement("span", "", `TASK ${String(task.index + 1).padStart(3, "0")} · ${task.id}`),
        createElement("span", "status-badge", task.status || "tracked"),
    );
    const meta = createElement("div", "inspector-meta");
    const metaValues = state.activeBenchId === "officeqa"
        ? [task.variantLabel, task.category, task.difficulty, ...task.outputFormats]
        : [task.category, task.difficulty, ...task.outputFormats];
    uniqueStrings(metaValues).filter(Boolean).forEach((value) => {
        meta.append(createElement("span", "tag-badge", value));
    });
    const taskTitle = createElement("h2", "", task.title);
    if (task.titleOriginal && task.titleOriginal !== task.title) {
        taskTitle.title = `英文原题：${task.titleOriginal}`;
    }
    header.append(kicker, taskTitle, meta);

    const promptSection = createTaskPromptSection(task);
    const previewSection = createPreviewSection(task);
    const goldProvenanceSection = createGoldProvenanceSection(task);
    const verifierSection = createVerifierSection(raw?.verifier || {}, task);
    const sections = [header, promptSection.section, previewSection];
    if (goldProvenanceSection) {
        sections.push(goldProvenanceSection);
    }
    sections.push(verifierSection);
    dom.taskInspector.replaceChildren(...sections);
    dom.taskInspector.scrollTop = 0;
}

function createTaskPromptSection(task) {
    const result = createInspectorSection("01 · TASK REQUIREMENT", "任务要求");
    const original = task.prompt || "官方任务文本未公开。";
    if (task.nativeChinese || isPrimarilyChinese(original)) {
        result.body.append(createElement("p", "prompt-block prompt-block-original", original));
        return result;
    }

    const tabs = createElement("div", "language-tabs");
    tabs.setAttribute("role", "tablist");
    tabs.setAttribute("aria-label", "切换任务要求语言");
    const zhButton = createElement("button", "language-tab active", "中文");
    const enButton = createElement("button", "language-tab", "English");
    const groupId = `task-language-${interactiveId += 1}`;
    zhButton.type = "button";
    enButton.type = "button";
    zhButton.id = `${groupId}-zh-tab`;
    enButton.id = `${groupId}-en-tab`;
    zhButton.setAttribute("role", "tab");
    enButton.setAttribute("role", "tab");
    zhButton.setAttribute("aria-controls", `${groupId}-zh-panel`);
    enButton.setAttribute("aria-controls", `${groupId}-en-panel`);
    tabs.append(zhButton, enButton);
    result.titleRow.append(tabs);

    const panels = createElement("div", "language-panels");
    const zhPanel = createElement("div", "language-panel active");
    const enPanel = createElement("div", "language-panel");
    zhPanel.id = `${groupId}-zh-panel`;
    enPanel.id = `${groupId}-en-panel`;
    zhPanel.setAttribute("role", "tabpanel");
    enPanel.setAttribute("role", "tabpanel");
    zhPanel.setAttribute("aria-labelledby", zhButton.id);
    enPanel.setAttribute("aria-labelledby", enButton.id);
    if (task.promptZh) {
        zhPanel.append(
            createElement(
                "span",
                "translation-status translation-status-ready",
                task.promptTranslationIsMachine ? "完整机器译文 · 可对照英文原文" : "完整中文译文",
            ),
            createElement("p", "prompt-block prompt-block-translation", task.promptZh),
        );
    }
    else {
        const pending = createElement("div", "translation-pending");
        pending.append(
            createElement("strong", "", "中文译文待补"),
            createElement(
                "p",
                "",
                "本站尚未收录经过明确标记的逐字完整译文。"
                    + "为避免把题目梗概冒充翻译，这里暂不展示旧的摘要字段。",
            ),
        );
        zhPanel.append(pending);
    }
    enPanel.append(
        createElement("span", "translation-status", "官方英文原文"),
        createElement("p", "prompt-block prompt-block-original", original),
    );
    panels.append(zhPanel, enPanel);
    result.body.append(panels);

    const activate = (language) => {
        const chinese = language === "zh";
        zhButton.classList.toggle("active", chinese);
        enButton.classList.toggle("active", !chinese);
        zhPanel.classList.toggle("active", chinese);
        enPanel.classList.toggle("active", !chinese);
        zhPanel.hidden = !chinese;
        enPanel.hidden = chinese;
        zhButton.setAttribute("aria-selected", String(chinese));
        enButton.setAttribute("aria-selected", String(!chinese));
        zhButton.tabIndex = chinese ? 0 : -1;
        enButton.tabIndex = chinese ? -1 : 0;
    };
    zhButton.addEventListener("click", () => activate("zh"));
    enButton.addEventListener("click", () => activate("en"));
    zhButton.addEventListener("keydown", (event) => {
        if (event.key === "ArrowRight" || event.key === "ArrowLeft") {
            event.preventDefault();
            activate("en");
            enButton.focus();
        }
    });
    enButton.addEventListener("keydown", (event) => {
        if (event.key === "ArrowRight" || event.key === "ArrowLeft") {
            event.preventDefault();
            activate("zh");
            zhButton.focus();
        }
    });
    activate("zh");
    return result;
}

function createGoldProvenanceSection(task) {
    if (state.activeBenchId !== "officeqa") {
        return null;
    }
    const provenance = task.raw?.gold_provenance;
    if (!provenance || typeof provenance !== "object") {
        return null;
    }
    const files = asArray(provenance.files);
    const declaredCount = firstNumber(provenance.source_file_count, files.length);
    const section = createElement("section", "inspector-section gold-provenance-section");
    const details = createElement("details", "gold-provenance-details");
    const summary = document.createElement("summary");
    const summaryCopy = document.createElement("span");
    summaryCopy.append(
        createElement("span", "gold-provenance-kicker", "GOLD PROVENANCE"),
        createElement("strong", "", "Gold 来源·仅审阅，不是模型输入"),
        createElement(
            "small",
            "",
            `${formatNumber(declaredCount)} 份文件 · 默认折叠 · 页码已剥离`,
        ),
    );
    summary.append(
        createElement("span", "gold-provenance-mark", "GOLD"),
        summaryCopy,
        createElement("span", "gold-provenance-caret", "⌄"),
    );

    const body = createElement("div", "gold-provenance-body");
    body.append(createElement(
        "p",
        "gold-provenance-note",
        firstString(
            provenance.note,
            "这是官方 Gold 来源映射，仅用于人工审阅；不会自动加入端到端 agent 输入。",
        ),
    ));
    const documentUrls = uniqueStrings(asArray(provenance.document_urls)).filter((url) => {
        return Boolean(safeHttpUrl(url));
    });
    if (documentUrls.length) {
        body.append(createGoldProvenanceUrlList(documentUrls));
    }
    const list = createElement("div", "gold-provenance-list");
    const progress = createElement("div", "gold-provenance-progress");
    const loadMore = createElement("button", "gold-provenance-more", "继续显示 20 份");
    loadMore.type = "button";
    progress.append(createElement("span", "", "尚未展开文件列表"), loadMore);
    body.append(list, progress);
    details.append(summary, body);
    section.append(details);

    let rendered = 0;
    const renderNext = () => {
        const next = files.slice(rendered, rendered + GOLD_PROVENANCE_BATCH_SIZE);
        const fragment = document.createDocumentFragment();
        next.forEach((file, index) => {
            fragment.append(createGoldProvenanceFile(file, rendered + index, provenance));
        });
        list.append(fragment);
        rendered += next.length;
        progress.querySelector("span").textContent = (
            `已显示 ${formatNumber(rendered)} / ${formatNumber(files.length)} 份文件`
        );
        loadMore.classList.toggle("hidden", rendered >= files.length);
    };
    loadMore.addEventListener("click", renderNext);
    details.addEventListener("toggle", () => {
        if (details.open && rendered === 0) {
            renderNext();
        }
    });
    return section;
}

function createGoldProvenanceUrlList(urls) {
    const block = createElement("div", "gold-provenance-urls");
    const head = document.createElement("div");
    head.append(
        createElement("strong", "", `FRASER 文档入口 ${formatNumber(urls.length)} 条`),
        createElement("span", "", "与文件清单独立呈现，不按数组位置配对"),
    );
    const list = createElement("div", "gold-provenance-url-list");
    urls.forEach((url, index) => {
        list.append(createExternalLink(
            `打开官方文档 ${String(index + 1).padStart(2, "0")} ↗`,
            url,
            "gold-provenance-url",
        ));
    });
    block.append(head, list);
    return block;
}

function createGoldProvenanceFile(file, index, provenance) {
    const rawFile = typeof file === "string" ? {filename: file} : (file || {});
    const filename = firstString(rawFile.filename, rawFile.name, `Gold source ${index + 1}`);
    const row = createElement("article", "gold-provenance-file");
    const copy = document.createElement("div");
    copy.append(
        createElement("strong", "", filename),
        createElement("small", "", goldProvenanceFileDescription(filename, provenance)),
    );
    const formats = createElement("div", "gold-provenance-formats");
    asArray(rawFile.representations).forEach((format) => {
        formats.append(createElement("span", "", provenanceFormatLabel(format)));
    });
    if (!formats.children.length) {
        formats.append(createElement("span", "", "来源映射"));
    }
    row.append(
        createElement("span", "gold-provenance-index", String(index + 1).padStart(2, "0")),
        copy,
        formats,
    );
    return row;
}

function goldProvenanceFileDescription(filename, provenance) {
    const descriptors = asArray(provenance?.documents).filter((document) => {
        return firstString(document?.corpus_file) === filename;
    });
    if (!descriptors.length) {
        return "官方文件名映射 · 来源描述未提供或独立保存";
    }
    const values = descriptors.flatMap((document) => [
        document?.year ? `年份 ${document.year}` : "",
        document?.month && document.month !== "N/A" ? document.month : "",
        document?.description && document.description !== "N/A" ? document.description : "",
    ]).filter(Boolean);
    return uniqueStrings(values).slice(0, 3).join(" · ") || "官方文件名映射";
}

function provenanceFormatLabel(value) {
    const format = String(value || "").trim().toLocaleLowerCase();
    if (format === "parsed_json") {
        return "Parsed JSON";
    }
    if (format === "txt") {
        return "TXT";
    }
    if (format === "pdf") {
        return "PDF";
    }
    return format ? format.toLocaleUpperCase() : "FILE";
}

function createPreviewSection(task) {
    const section = createElement("section", "inspector-section");
    const titleRow = createElement("div", "inspector-section-title");
    const tabs = createElement("div", "preview-tabs");
    const inputButton = createElement("button", "preview-tab active", "输入");
    const isOfficeQa = state.activeBenchId === "officeqa";
    const outputButton = createElement(
        "button",
        "preview-tab",
        isOfficeQa ? "答案格式" : "产物",
    );
    inputButton.type = "button";
    outputButton.type = "button";
    tabs.append(inputButton, outputButton);
    titleRow.append(
        createElement("h3", "", isOfficeQa ? "02 · 输入与答案" : "02 · 文件与站内预览"),
        tabs,
    );
    const content = document.createElement("div");
    section.append(titleRow, content);

    const inputMaterials = mergeIndexedMaterials(normalizeInputMaterials(task), task, "input");
    const outputMaterials = mergeIndexedMaterials(normalizeOutputMaterials(task), task, "output");
    const activate = (slot) => {
        const isInput = slot === "input";
        inputButton.classList.toggle("active", isInput);
        outputButton.classList.toggle("active", !isInput);
        inputButton.setAttribute("aria-pressed", String(isInput));
        outputButton.setAttribute("aria-pressed", String(!isInput));
        if (!isInput && isOfficeQa) {
            renderOfficeQaAnswerContract(content, task);
            return;
        }
        renderMaterialPanel(content, isInput ? inputMaterials : outputMaterials, task, slot);
    };
    inputButton.addEventListener("click", () => activate("input"));
    outputButton.addEventListener("click", () => activate("output"));
    activate("input");
    return section;
}

function renderOfficeQaAnswerContract(container, task) {
    container.replaceChildren();
    const panel = createElement("div", "officeqa-answer-contract");
    const head = createElement("div", "officeqa-answer-head");
    const copy = document.createElement("div");
    copy.append(
        createElement("span", "officeqa-answer-kicker", "ANSWER CONTRACT"),
        createElement("h4", "", "提交直接答案；Gold answer withheld"),
        createElement(
            "p",
            "",
            "OfficeQA 的输出是一个可确定性评分的文本答案，不是 PDF、Office 或 Web 产物。",
        ),
    );
    const sample = createElement("pre", "officeqa-answer-sample");
    sample.append(createElement("code", "", "<FINAL_ANSWER>\n  your direct answer\n</FINAL_ANSWER>"));
    head.append(copy, sample);

    const rules = createElement("ol", "officeqa-answer-rules");
    [
        "只评分最后一个 FINAL_ANSWER 块；缺失或标签格式错误即失败。",
        "答案保持单个非空行、最多 250 字符，不追加解释、Markdown 或推理过程。",
        "评分器会归一化货币、百分比、括号负数、量级单位、标签与列表。",
        "Gold answer、答案哈希、长度和逐题答案形态均未进入浏览器数据。",
    ].forEach((rule, index) => {
        const item = document.createElement("li");
        item.append(
            createElement("span", "", String(index + 1).padStart(2, "0")),
            createElement("p", "", rule),
        );
        rules.append(item);
    });

    const revision = createElement("div", "officeqa-answer-foot");
    revision.append(
        createElement("span", "", officeQaTaskLabel(task)),
        createElement(
            "span",
            "",
            task.datasetRevision ? `Dataset revision · ${shortRevision(task.datasetRevision)}` : "Dataset revision · pending",
        ),
        createElement("strong", "", "答案排除策略已启用"),
    );
    panel.append(head, rules, revision);
    container.append(panel);
}

function renderMaterialPanel(container, materials, task, slot) {
    container.replaceChildren();
    if (!materials.length) {
        const fallback = createElement("div", "preview-unavailable");
        const copy = document.createElement("div");
        copy.append(
            createElement("span", "preview-unavailable-icon", slot === "input" ? "IN" : "OUT"),
            createElement("h4", "", slot === "input" ? "没有公开输入文件" : "没有公开端到端产物"),
            createElement(
                "p",
                "",
                slot === "input"
                    ? "该条目可能是协议单元、gated 数据，或官方只公布任务说明。"
                    : "任务、rubric 与 verifier 公开并不等于参评模型产物公开。镜像生成后会在这里自动出现。",
            ),
        );
        fallback.append(copy);
        container.append(fallback);
        return;
    }

    const list = createElement("div", "material-list");
    const previewHost = document.createElement("div");
    materials.forEach((material, index) => {
        const match = getMaterialIndexMatch(material, task, slot);
        const indexedRecord = match?._previewRecord || match?._mirrorRecord;
        const indexedFormat = fileExtension(firstString(
            indexedRecord?.preview_url,
            indexedRecord?.logical_path,
            indexedRecord?.view_path,
        )).toUpperCase();
        const provenanceLabel = resolveMaterialProvenance(material, task, slot);
        const displayName = material.isFallbackName && provenanceLabel.includes("候选")
            ? "官方候选产物"
            : material.name;
        const button = createElement("button", `material-button${index === 0 ? " active" : ""}`);
        button.type = "button";
        button.append(
            createElement("strong", "", displayName),
            createElement(
                "small",
                "",
                `${material.format || indexedFormat || "FILE"} · ${provenanceLabel || material.availability || "unknown"}`,
            ),
        );
        button.addEventListener("click", () => {
            list.querySelectorAll(".material-button").forEach((item) => item.classList.remove("active"));
            button.classList.add("active");
            renderMaterialPreview(previewHost, material, task, slot);
        });
        list.append(button);
    });
    container.append(list, previewHost);
    renderMaterialPreview(previewHost, materials[0], task, slot);
}

function renderMaterialPreview(host, material, task, slot) {
    host.replaceChildren();
    const spec = resolvePreviewSpec(material, task, slot);
    const frame = createElement("div", "preview-frame");
    host.append(frame);

    if (spec.kind === "pages" && spec.pageImages.length) {
        renderPageImagePreview(frame, spec);
    }
    else if (spec.kind === "spreadsheet" && spec.spreadsheetManifestUrl) {
        void renderSpreadsheetPreview(frame, spec);
    }
    else if (spec.kind === "pdf" && spec.localUrl) {
        void renderValidatedLocalPreview(frame, material, spec, "pdf");
    }
    else if (spec.kind === "html" && spec.localUrl && spec.sanitizedHtml) {
        const iframe = document.createElement("iframe");
        iframe.title = `${material.name} HTML 预览`;
        iframe.loading = "lazy";
        iframe.setAttribute("sandbox", spec.iframeSandbox);
        iframe.referrerPolicy = "no-referrer";
        iframe.src = spec.localUrl;
        frame.append(iframe);
    }
    else if (spec.kind === "image" && spec.localUrl) {
        void renderValidatedLocalPreview(frame, material, spec, "image");
    }
    else if (spec.kind === "text") {
        renderTextPreview(frame, spec);
    }
    else {
        renderUnavailablePreview(frame, material, spec, slot, task);
    }

    if (shouldOfferOriginalDownload(spec)) {
        const actions = createElement("div", "preview-source-actions");
        actions.append(createExternalLink(
            "下载原始文件 ↗",
            spec.mirrorUrl,
            "external-link-button",
        ));
        host.append(actions);
    }

    const previewNote = spec.kind === "spreadsheet"
        ? "工作表采用惰性静态单元格视图；公式仅展示、不执行，PDF 只作为打印视图。"
        : spec.localUrl || spec.mirrorUrl || spec.pageImages.length || spec.textChunks.length
        ? "本站镜像优先；转换视图与原始文件分别标注。"
        : "为避免意外下载与跨站追踪，官方外链不会自动嵌入或请求。";
    const note = createElement(
        "p",
        "preview-note",
        spec.provenanceLabel ? `${spec.provenanceLabel}。${previewNote}` : previewNote,
    );
    host.append(note);
}

function shouldOfferOriginalDownload(spec) {
    const mirrorExtension = fileExtension(spec?.mirrorUrl);
    return Boolean(
        spec?.kind !== "missing"
        && spec?.mirrorReady
        && spec?.mirrorUrl
        && spec.mirrorUrl !== spec.localUrl
        && !["html", "htm"].includes(mirrorExtension)
    );
}

async function renderValidatedLocalPreview(frame, material, spec, kind) {
    if (shouldPreflightPreview(spec)) {
        frame.append(createElement("div", "preview-loading", "正在校验站内预览…"));
        try {
            await preflightLocalPreviewResource(spec.localUrl, kind);
        }
        catch (error) {
            if (frame.isConnected) {
                frame.replaceChildren();
                renderPreviewResourceFailure(frame, material, spec, error);
            }
            return;
        }
        if (!frame.isConnected) {
            return;
        }
        frame.replaceChildren();
    }

    if (kind === "pdf") {
        const iframe = document.createElement("iframe");
        iframe.title = `${material.name} PDF 预览`;
        iframe.loading = "lazy";
        iframe.src = spec.localUrl;
        frame.append(iframe);
        return;
    }

    const wrap = createElement("div", "preview-image-wrap");
    const image = document.createElement("img");
    image.loading = "lazy";
    image.alt = `${material.name} 预览`;
    image.addEventListener("error", () => {
        if (!frame.isConnected) {
            return;
        }
        frame.replaceChildren();
        renderPreviewResourceFailure(frame, material, spec, new Error("图片资源加载失败"));
    }, {once: true});
    image.src = spec.localUrl;
    wrap.append(image);
    frame.append(wrap);
}

function shouldPreflightPreview(spec) {
    return Boolean(spec.localUrl && !spec.previewBound && !spec.mirrorBound);
}

async function preflightLocalPreviewResource(url, kind) {
    if (!isLocalUrl(url)) {
        throw new Error("只允许校验本站预览资源");
    }
    let response = await fetch(url, {
        method: "HEAD",
        cache: "no-store",
        credentials: "same-origin",
    });
    let rangedResponse = false;
    if ([405, 501].includes(response.status)) {
        response = await fetch(url, {
            method: "GET",
            headers: {Range: "bytes=0-0"},
            cache: "no-store",
            credentials: "same-origin",
        });
        rangedResponse = true;
    }
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
    }
    const contentType = firstString(response.headers?.get?.("content-type"));
    if (!contentTypeMatchesPreviewKind(kind, contentType, url)) {
        if (rangedResponse && response.body?.cancel) {
            void response.body.cancel();
        }
        throw new Error(contentType
            ? `服务器返回了 ${contentType.split(";")[0]}，不是可用的 ${kind.toUpperCase()} 资源`
            : "服务器没有返回可验证的 Content-Type");
    }
    if (rangedResponse && response.body?.cancel) {
        void response.body.cancel();
    }
    return {contentType};
}

function contentTypeMatchesPreviewKind(kind, contentType, url = "") {
    const normalized = String(contentType || "").split(";")[0].trim().toLocaleLowerCase();
    const extension = fileExtension(url);
    if (kind === "pdf") {
        return normalized === "application/pdf";
    }
    if (kind === "image") {
        return normalized.startsWith("image/");
    }
    if (kind === "html") {
        return ["text/html", "application/xhtml+xml"].includes(normalized);
    }
    if (kind === "text") {
        if (["text/html", "application/xhtml+xml"].includes(normalized)) {
            return false;
        }
        if (normalized.startsWith("text/")) {
            return true;
        }
        if (/^application\/(?:[a-z0-9.+-]*\+)?(?:json|xml)$/.test(normalized)
            || ["application/x-ndjson", "application/jsonl"].includes(normalized)) {
            return true;
        }
        return normalized === "application/octet-stream"
            && ["json", "jsonl", "txt", "md", "csv", "tsv", "xml", "yaml", "yml"].includes(extension);
    }
    return false;
}

function renderPreviewResourceFailure(frame, material, spec, error) {
    frame.classList.add("preview-unavailable");
    const copy = document.createElement("div");
    copy.append(
        createElement("span", "preview-unavailable-icon", material.format || "FILE"),
        createElement("h4", "", "站内预览地址已失效"),
        createElement(
            "p",
            "",
            `该地址没有返回预期文件，已停止内嵌，避免把错误页当成产物展示。${error?.message ? `（${error.message}）` : ""}`,
        ),
    );
    if (spec.externalUrl) {
        copy.append(createExternalLink("主动打开官方来源 ↗", spec.externalUrl, "external-link-button"));
    }
    frame.append(copy);
}

function renderPageImagePreview(frame, spec) {
    let pageIndex = 0;
    const bar = createElement("div", "preview-page-bar");
    const previous = createElement("button", "", "← 上一页");
    const counter = createElement("span");
    const next = createElement("button", "", "下一页 →");
    previous.type = "button";
    next.type = "button";
    const imageWrap = createElement("div", "preview-image-wrap");
    const image = document.createElement("img");
    image.loading = "lazy";
    image.alt = "分页预览";
    imageWrap.append(image);
    const update = () => {
        image.src = spec.pageImages[pageIndex];
        counter.textContent = `第 ${pageIndex + 1} / ${spec.pageImages.length} 页`;
        previous.disabled = pageIndex === 0;
        next.disabled = pageIndex === spec.pageImages.length - 1;
    };
    previous.addEventListener("click", () => {
        pageIndex = Math.max(0, pageIndex - 1);
        update();
    });
    next.addEventListener("click", () => {
        pageIndex = Math.min(spec.pageImages.length - 1, pageIndex + 1);
        update();
    });
    bar.append(previous, counter, next);
    frame.append(bar, imageWrap);
    update();
}

async function renderSpreadsheetPreview(frame, spec) {
    frame.replaceChildren(createElement("div", "preview-loading", "正在读取安全工作簿索引…"));
    try {
        const manifest = await fetchSpreadsheetJson(
            spec.spreadsheetManifestUrl,
            SPREADSHEET_MANIFEST_MAX_BYTES,
        );
        validateSpreadsheetManifest(manifest, spec);
        if (!frame.isConnected) {
            return;
        }
        const shell = createElement("div", "spreadsheet-preview");
        const tabs = createElement("div", "spreadsheet-tabs");
        tabs.setAttribute("role", "tablist");
        const stage = createElement("div", "spreadsheet-stage");
        manifest.sheets.forEach((sheet, index) => {
            const button = createElement(
                "button",
                `spreadsheet-tab${index === 0 ? " active" : ""}`,
                `${sheet.name}${sheet.state === "visible" ? "" : "（隐藏）"}`,
            );
            button.type = "button";
            button.setAttribute("role", "tab");
            button.setAttribute("aria-selected", index === 0 ? "true" : "false");
            button.addEventListener("click", () => {
                tabs.querySelectorAll(".spreadsheet-tab").forEach((item) => {
                    item.classList.remove("active");
                    item.setAttribute("aria-selected", "false");
                });
                button.classList.add("active");
                button.setAttribute("aria-selected", "true");
                void renderSpreadsheetSheet(stage, sheet, spec);
            });
            tabs.append(button);
        });
        const workbookView = createElement("div", "spreadsheet-workbook-view");
        workbookView.append(tabs, stage);
        if (spec.printViewUrl) {
            const viewTabs = createElement("div", "spreadsheet-view-tabs");
            const sheetButton = createElement("button", "active", "工作表");
            const printButton = createElement("button", "", "打印视图");
            const printView = createElement("div", "spreadsheet-print-view hidden");
            const iframe = document.createElement("iframe");
            iframe.title = "工作簿打印视图";
            iframe.loading = "lazy";
            iframe.dataset.src = spec.printViewUrl;
            printView.append(iframe);
            sheetButton.type = "button";
            printButton.type = "button";
            sheetButton.addEventListener("click", () => {
                sheetButton.classList.add("active");
                printButton.classList.remove("active");
                workbookView.classList.remove("hidden");
                printView.classList.add("hidden");
            });
            printButton.addEventListener("click", () => {
                printButton.classList.add("active");
                sheetButton.classList.remove("active");
                workbookView.classList.add("hidden");
                printView.classList.remove("hidden");
                if (!iframe.src) {
                    iframe.src = iframe.dataset.src;
                }
            });
            viewTabs.append(sheetButton, printButton);
            shell.append(viewTabs, workbookView, printView);
        }
        else {
            shell.append(workbookView);
        }
        frame.replaceChildren(shell);
        await renderSpreadsheetSheet(stage, manifest.sheets[0], spec);
    }
    catch (error) {
        if (!frame.isConnected) {
            return;
        }
        frame.replaceChildren();
        renderPreviewResourceFailure(frame, {format: "XLS"}, spec, error);
    }
}

async function renderSpreadsheetSheet(stage, sheet, spec) {
    const header = createElement("div", "spreadsheet-sheet-header");
    const title = createElement("strong", "", sheet.name);
    const details = createElement(
        "span",
        "",
        `${formatNumber(sheet.cell_count)} 个非空单元格 · ${formatNumber(sheet.formula_count)} 个公式`
        + `${sheet.merged_ranges.length ? ` · ${formatNumber(sheet.merged_ranges.length)} 个合并区域` : ""}`,
    );
    header.append(title, details);
    const cellList = createElement("div", "spreadsheet-cell-list");
    const controls = createElement("div", "spreadsheet-chunk-controls");
    const status = createElement("span", "", "按需读取单元格片段");
    const more = createElement("button", "", "继续加载");
    more.type = "button";
    controls.append(status, more);
    stage.replaceChildren(header, cellList, controls);
    let chunkIndex = 0;
    const appendNext = async () => {
        if (chunkIndex >= sheet.chunks.length) {
            more.classList.add("hidden");
            status.textContent = `已显示全部 ${formatNumber(sheet.cell_count)} 个非空单元格`;
            return;
        }
        more.disabled = true;
        try {
            const declaration = sheet.chunks[chunkIndex];
            const chunkUrl = resolvePreviewAssetUrl(declaration.path);
            assertTrustedSpreadsheetChunkPath(chunkUrl, spec.spreadsheetManifestUrl);
            const chunk = await fetchSpreadsheetJson(chunkUrl, SPREADSHEET_CHUNK_MAX_BYTES);
            validateSpreadsheetChunk(chunk, declaration, sheet.id);
            cellList.append(renderSpreadsheetChunk(chunk));
            chunkIndex += 1;
            more.classList.toggle("hidden", chunkIndex >= sheet.chunks.length);
            status.textContent = `已加载 ${chunkIndex} / ${sheet.chunks.length} 个片段`;
        }
        catch (error) {
            status.textContent = `工作表片段读取失败：${error.message}`;
        }
        finally {
            more.disabled = false;
        }
    };
    more.addEventListener("click", appendNext);
    await appendNext();
}

function renderSpreadsheetChunk(chunk) {
    const section = createElement("section", "spreadsheet-chunk");
    const bounds = chunk.bounds || {};
    section.append(createElement(
        "div",
        "spreadsheet-chunk-range",
        `${spreadsheetCellLabel(bounds.row0, bounds.col0)} – ${spreadsheetCellLabel(bounds.row1, bounds.col1)}`,
    ));
    chunk.cells.forEach((cell) => {
        const row = createElement("div", "spreadsheet-cell-row");
        row.append(
            createElement("code", "spreadsheet-cell-address", spreadsheetCellLabel(cell.r, cell.c)),
            createElement("span", "spreadsheet-cell-value", cell.display ?? cell.v ?? ""),
            createElement("code", "spreadsheet-cell-formula", cell.f ? `=${cell.f}` : ""),
        );
        section.append(row);
    });
    return section;
}

function spreadsheetCellLabel(row, column) {
    let value = Number(column);
    let label = "";
    while (Number.isInteger(value) && value > 0) {
        value -= 1;
        label = String.fromCharCode(65 + (value % 26)) + label;
        value = Math.floor(value / 26);
    }
    return `${label || "?"}${Number.isInteger(Number(row)) ? Number(row) : "?"}`;
}

async function fetchSpreadsheetJson(url, maximumBytes) {
    if (!isTrustedSpreadsheetPreviewPath(url)) {
        throw new Error("工作簿视图地址不在受信任的本站目录");
    }
    const response = await fetch(url, {
        cache: "no-store",
        credentials: "same-origin",
    });
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
    }
    const declaredLength = Number(response.headers?.get?.("content-length") || 0);
    if (declaredLength > maximumBytes) {
        throw new Error("工作簿视图超过安全读取上限");
    }
    const encoded = new Uint8Array(await response.arrayBuffer());
    if (encoded.byteLength > maximumBytes) {
        throw new Error("工作簿视图超过安全读取上限");
    }
    let text;
    if (encoded[0] === 0x1f && encoded[1] === 0x8b) {
        if (typeof DecompressionStream !== "function") {
            throw new Error("当前浏览器不支持安全 gzip 工作表片段");
        }
        const stream = new Blob([encoded]).stream().pipeThrough(new DecompressionStream("gzip"));
        text = await new Response(stream).text();
    }
    else {
        text = new TextDecoder("utf-8", {fatal: true}).decode(encoded);
    }
    if (new TextEncoder().encode(text).byteLength > maximumBytes) {
        throw new Error("解压后的工作簿视图超过安全读取上限");
    }
    return JSON.parse(text);
}

function validateSpreadsheetManifest(manifest, spec) {
    if (!manifest || manifest.schema_version !== 1 || manifest.profile !== TRUSTED_SPREADSHEET_SECURITY_PROFILE) {
        throw new Error("工作簿 manifest 安全版本不受支持");
    }
    if (spec.sourceSha256 && manifest.source_sha256 !== spec.sourceSha256) {
        throw new Error("工作簿 manifest 与原始文件不匹配");
    }
    if (!Array.isArray(manifest.sheets) || !manifest.sheets.length || manifest.sheets.length > 2048) {
        throw new Error("工作簿 sheet 清单无效");
    }
    let totalChunks = 0;
    manifest.sheets.forEach((sheet) => {
        if (!sheet || typeof sheet.id !== "string" || typeof sheet.name !== "string"
            || !Array.isArray(sheet.chunks) || !Array.isArray(sheet.merged_ranges)) {
            throw new Error("工作簿 sheet 元数据无效");
        }
        totalChunks += sheet.chunks.length;
        sheet.chunks.forEach((chunk) => {
            const chunkUrl = resolvePreviewAssetUrl(chunk?.path);
            assertTrustedSpreadsheetChunkPath(chunkUrl, spec.spreadsheetManifestUrl);
        });
    });
    if (totalChunks > 10000) {
        throw new Error("工作簿片段数量超过安全上限");
    }
}

function validateSpreadsheetChunk(chunk, declaration, sheetId) {
    if (!chunk || chunk.schema_version !== 1 || chunk.sheet_id !== sheetId
        || !Array.isArray(chunk.cells) || chunk.cells.length > 5000) {
        throw new Error("工作表片段结构无效");
    }
    if (Number(declaration.cells) !== chunk.cells.length) {
        throw new Error("工作表片段单元格计数不一致");
    }
    chunk.cells.forEach((cell) => {
        if (!Number.isInteger(cell?.r) || cell.r < 1 || !Number.isInteger(cell?.c) || cell.c < 1) {
            throw new Error("工作表片段包含无效坐标");
        }
    });
}

function assertTrustedSpreadsheetChunkPath(chunkUrl, manifestUrl) {
    if (!isTrustedSpreadsheetPreviewPath(chunkUrl)) {
        throw new Error("工作表片段地址不受信任");
    }
    const root = new URL(manifestUrl, document.baseURI).pathname.replace(/\/manifest\.json$/, "/");
    const chunkPath = new URL(chunkUrl, document.baseURI).pathname;
    if (!chunkPath.startsWith(`${root}sheets/`) || !chunkPath.endsWith(".json.gz")) {
        throw new Error("工作表片段离开其内容寻址目录");
    }
}

function renderTextPreview(frame, spec) {
    const controls = createElement("div", "preview-text-controls");
    const status = createElement("span", "", "局部预览 · 按需继续读取");
    const more = createElement("button", "", "继续加载");
    more.type = "button";
    const output = createElement("pre", "preview-text");
    controls.append(status, more);
    frame.append(controls, output);

    let chunkIndex = 0;
    let byteOffset = 0;
    const appendNext = async () => {
        more.disabled = true;
        try {
            if (spec.textChunks.length) {
                if (chunkIndex >= spec.textChunks.length) {
                    more.classList.add("hidden");
                    status.textContent = `已显示 ${formatNumber(output.textContent.length)} 字符`;
                    return;
                }
                const chunk = spec.textChunks[chunkIndex];
                output.textContent += await resolveTextChunk(chunk);
                chunkIndex += 1;
                more.classList.toggle("hidden", chunkIndex >= spec.textChunks.length);
                status.textContent = `已加载 ${chunkIndex} / ${spec.textChunks.length} 个片段`;
            }
            else if (spec.localUrl) {
                const result = await fetchLocalTextSlice(spec.localUrl, byteOffset, TEXT_PREVIEW_CHARS);
                output.textContent += result.text;
                byteOffset = result.nextOffset;
                more.classList.toggle("hidden", result.done);
                status.textContent = `${formatNumber(byteOffset)} 字符已显示`;
            }
            else {
                more.classList.add("hidden");
                output.textContent = "没有可读取的站内文本镜像。";
            }
        }
        catch (error) {
            status.textContent = `片段读取失败：${error.message}`;
        }
        finally {
            more.disabled = false;
        }
    };
    more.addEventListener("click", appendNext);
    void appendNext();
}

async function resolveTextChunk(chunk) {
    if (typeof chunk === "string") {
        const chunkUrl = looksLikeUrl(chunk) ? resolvePreviewAssetUrl(chunk) : "";
        if (chunkUrl && isLocalUrl(chunkUrl)) {
            const response = await fetch(chunkUrl, {cache: "no-store"});
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            assertTextPreviewResponse(response, chunkUrl);
            return response.text();
        }
        return `${chunk}\n`;
    }
    if (typeof chunk?.text === "string") {
        return `${chunk.text}\n`;
    }
    const url = firstString(chunk?.local_url, chunk?.url, chunk?.path);
    const chunkUrl = resolvePreviewAssetUrl(url);
    if (chunkUrl && isLocalUrl(chunkUrl)) {
        const response = await fetch(chunkUrl, {cache: "no-store"});
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        assertTextPreviewResponse(response, chunkUrl);
        return response.text();
    }
    return "";
}

async function fetchLocalTextSlice(url, start, size) {
    if (!isLocalUrl(url)) {
        throw new Error("只允许读取本站文本镜像");
    }
    let fullText = localTextCache.get(url);
    if (typeof fullText !== "string") {
        const response = await fetch(url, {cache: "no-store"});
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        assertTextPreviewResponse(response, url);
        fullText = await response.text();
        localTextCache.set(url, fullText);
        while (localTextCache.size > LOCAL_TEXT_CACHE_LIMIT) {
            localTextCache.delete(localTextCache.keys().next().value);
        }
    }
    else {
        localTextCache.delete(url);
        localTextCache.set(url, fullText);
    }
    const text = fullText.slice(start, start + size);
    return {
        text,
        nextOffset: start + text.length,
        done: start + text.length >= fullText.length,
    };
}

function assertTextPreviewResponse(response, url) {
    const contentType = firstString(response.headers?.get?.("content-type"));
    if (!contentTypeMatchesPreviewKind("text", contentType, url)) {
        throw new Error(contentType
            ? `服务器返回了 ${contentType.split(";")[0]}，不是可预览文本`
            : "服务器没有返回可验证的文本 Content-Type");
    }
}

function renderUnavailablePreview(frame, material, spec, slot, task) {
    frame.classList.add("preview-unavailable");
    const copy = document.createElement("div");
    let title = "站内预览正在补齐";
    let description = "数据条目已经收录；转换后的 PDF、分页 WebP、JSONL 片段或安全 HTML 会在构建完成后出现。";
    const artifactStatus = firstString(task?.raw?.artifact?.status).toLocaleLowerCase();
    if (spec.integrityNote) {
        title = "上游原件本身不完整";
        description = spec.integrityNote;
    }
    else if (slot === "output" && artifactStatus === "not_published") {
        title = "官方未发布参评模型产物";
        description = "公开的任务、Gold 数据或 verifier 不等于公开的参评模型交付物。";
    }
    else if (spec.mirrorReady) {
        title = "原始文件已公开，等待可视化转换";
        description = "可先直接打开或下载经校验的原件；浏览器不能原生展示的 Office 或专用格式会再补 PDF、图片或结构化预览。HTML 原件不会被直接执行。";
    }
    else if (spec.protectedMirrored) {
        title = spec.previewState === "corpus_only"
            ? "来源文件受许可限制，公开版未分发"
            : "文件已镜像，当前不公开下载";
        description = "来源记录显示文件已保存并校验；由于格式、许可或安全边界，公开版不提供原件或可内嵌预览。";
    }
    else if (spec.indexesLoaded && spec.benchHasIndexedAssets) {
        title = "镜像未绑定到此任务";
        description = "这个 Bench 已有站内镜像，但当前材料没有命中 task id、source line、仓库路径、归档成员、来源 URL 或文件名。";
    }
    else if (spec.externalUrl) {
        title = "官方文件尚未镜像到本站";
        description = "外部文件不会自动加载。你可以主动打开官方来源，或等待站内镜像与转换结果。";
    }
    copy.append(
        createElement("span", "preview-unavailable-icon", material.format || (slot === "input" ? "IN" : "OUT")),
        createElement("h4", "", title),
        createElement(
            "p",
            "",
            spec.integrityNote || material.note || description,
        ),
    );
    const mirrorExtension = fileExtension(spec.mirrorUrl);
    if (spec.mirrorReady && spec.mirrorUrl && !["html", "htm"].includes(mirrorExtension)) {
        copy.append(createExternalLink(
            "打开 / 下载原始文件 ↗",
            spec.mirrorUrl,
            "external-link-button",
        ));
    }
    else if (spec.externalUrl) {
        copy.append(createExternalLink("主动打开官方来源 ↗", spec.externalUrl, "external-link-button"));
    }
    frame.append(copy);
}

function createVerifierSection(verifier, task) {
    const result = createInspectorSection("03 · VERIFIER", "Verifier 设计");
    const indexed = getIndexedVerifierSource(task);
    const sourceSummary = firstString(verifier?.summary);
    result.body.append(createElement(
        "p",
        "verifier-summary",
        firstString(
            verifier?.summary_zh_exact,
            verifier?.summary_zh,
            isPrimarilyChinese(sourceSummary) ? sourceSummary : "",
            indexed?.sources?.config?.explanation_zh,
            sourceSummary,
            "该条目的评分协议或确定性检查尚未写入目录。",
        ),
    ));
    const checks = asArray(verifier?.checks || verifier?.rubrics);
    if (checks.length) {
        const list = createElement("ol", "check-list");
        checks.forEach((check, index) => {
            const item = createElement("li", "check-item");
            const copy = createElement("div", "check-copy");
            const sourceTitle = firstString(
                check?.name,
                check?.title,
                check?.path,
                check?.dimension,
                check?.id,
            );
            const originalTitle = sourceTitle || `检查 ${index + 1}`;
            const originalDescription = firstString(
                check?.description,
                check?.criterion,
                check?.assertion,
                check?.requirement,
            );
            const languageSwitcher = createVerifierCheckLanguageSwitcher(
                check,
                index,
                sourceTitle,
                originalTitle,
                originalDescription,
            );
            if (languageSwitcher) {
                copy.append(languageSwitcher);
            }
            else {
                appendVerifierCheckCopy(
                    copy,
                    originalTitle,
                    originalDescription,
                    "original",
                );
            }
            item.append(createElement("span", "check-index", String(index + 1).padStart(2, "0")), copy);
            list.append(item);
        });
        result.body.append(list);
    }
    result.body.append(createVerifierEvidence(verifier, task));
    return result.section;
}

function verifierCheckTranslation(check) {
    const titleStatus = firstString(check?.title_translation_status).toLocaleLowerCase();
    const descriptionStatus = firstString(
        check?.description_translation_status,
    ).toLocaleLowerCase();
    const translatedTitle = firstString(
        check?.name_zh_exact,
        check?.title_zh_exact,
        check?.name_zh,
        check?.title_zh,
        check?.translation_zh?.title,
        check?.translations?.zh?.title,
    );
    const translatedDescription = firstString(
        check?.description_zh_exact,
        check?.criterion_zh_exact,
        check?.assertion_zh_exact,
        check?.requirement_zh_exact,
        check?.description_zh,
        check?.criterion_zh,
        check?.assertion_zh,
        check?.requirement_zh,
        check?.translation_zh?.description,
        check?.translations?.zh?.description,
    );
    const translationMethod = firstString(
        check?.translation_method,
        check?.title_translation_method,
        check?.description_translation_method,
    ).toLocaleLowerCase();
    return {
        title: translatedTitle,
        description: translatedDescription,
        titleUsable: isUsableVerifierTranslation(translatedTitle, titleStatus),
        descriptionUsable: isUsableVerifierTranslation(
            translatedDescription,
            descriptionStatus,
        ),
        isMachine: translationMethod.includes("machine"),
    };
}

function isUsableVerifierTranslation(value, status) {
    const chineseCount = (String(value || "").match(/[\u3400-\u9fff]/g) || []).length;
    const rejectedStatus = /missing|needs_review|summary|partial/i.test(String(status || ""));
    return chineseCount >= 2 && !rejectedStatus;
}

function appendVerifierCheckCopy(container, title, description, language) {
    if (title) {
        container.append(createElement("strong", `check-title-${language}`, title));
    }
    if (description) {
        container.append(createElement("p", `check-description-${language}`, description));
    }
}

function createVerifierCheckLanguageSwitcher(
    check,
    index,
    sourceTitle,
    originalTitle,
    originalDescription,
) {
    const originalText = `${sourceTitle} ${originalDescription}`.trim();
    if (isPrimarilyChinese(originalText)) {
        return null;
    }
    const translation = verifierCheckTranslation(check);
    const identifierOnlyTitle = !firstString(
        check?.name,
        check?.title,
        check?.path,
        check?.dimension,
    ) && Boolean(firstString(check?.id));
    const titleReady = !sourceTitle
        || isPrimarilyChinese(sourceTitle)
        || translation.titleUsable
        || identifierOnlyTitle;
    const descriptionReady = !originalDescription
        || isPrimarilyChinese(originalDescription)
        || translation.descriptionUsable;
    const hasTranslatedField = translation.titleUsable || translation.descriptionUsable;
    if (!titleReady || !descriptionReady || !hasTranslatedField) {
        return null;
    }

    const wrapper = createElement("div", "check-language-switcher");
    const tabs = createElement("div", "check-language-tabs");
    const zhButton = createElement("button", "check-language-tab active", "中文");
    const enButton = createElement("button", "check-language-tab", "English");
    const panels = createElement("div", "check-language-panels");
    const zhPanel = createElement("div", "check-language-panel active");
    const enPanel = createElement("div", "check-language-panel");
    const groupId = `verifier-check-language-${interactiveId += 1}`;
    const chineseTitle = translation.titleUsable
        ? translation.title
        : identifierOnlyTitle
            ? `检查项 ${sourceTitle}`
            : originalTitle;
    const chineseDescription = translation.descriptionUsable
        ? translation.description
        : originalDescription;

    tabs.setAttribute("role", "tablist");
    tabs.setAttribute("aria-label", `切换第 ${index + 1} 个 Verifier 检查项语言`);
    zhButton.type = "button";
    enButton.type = "button";
    zhButton.id = `${groupId}-zh-tab`;
    enButton.id = `${groupId}-en-tab`;
    zhButton.title = "查看中文翻译";
    enButton.title = "查看英文原文";
    zhButton.setAttribute("role", "tab");
    enButton.setAttribute("role", "tab");
    zhButton.setAttribute("aria-controls", `${groupId}-zh-panel`);
    enButton.setAttribute("aria-controls", `${groupId}-en-panel`);
    tabs.append(zhButton, enButton);

    zhPanel.id = `${groupId}-zh-panel`;
    enPanel.id = `${groupId}-en-panel`;
    zhPanel.setAttribute("role", "tabpanel");
    enPanel.setAttribute("role", "tabpanel");
    zhPanel.setAttribute("aria-labelledby", zhButton.id);
    enPanel.setAttribute("aria-labelledby", enButton.id);
    zhPanel.append(createElement(
        "span",
        "check-language-status check-language-status-ready",
        translation.isMachine ? "完整机器译文 · 可切回英文核对" : "完整中文译文",
    ));
    appendVerifierCheckCopy(zhPanel, chineseTitle, chineseDescription, "translation");
    enPanel.append(createElement("span", "check-language-status", "官方英文原文"));
    appendVerifierCheckCopy(enPanel, originalTitle, originalDescription, "original");
    panels.append(zhPanel, enPanel);
    wrapper.append(tabs, panels);

    const activate = (language) => {
        const chinese = language === "zh";
        zhButton.classList.toggle("active", chinese);
        enButton.classList.toggle("active", !chinese);
        zhPanel.classList.toggle("active", chinese);
        enPanel.classList.toggle("active", !chinese);
        zhPanel.hidden = !chinese;
        enPanel.hidden = chinese;
        zhButton.setAttribute("aria-selected", String(chinese));
        enButton.setAttribute("aria-selected", String(!chinese));
        zhButton.tabIndex = chinese ? 0 : -1;
        enButton.tabIndex = chinese ? -1 : 0;
    };
    const moveTo = (language, button) => {
        activate(language);
        button.focus();
    };
    zhButton.addEventListener("click", () => activate("zh"));
    enButton.addEventListener("click", () => activate("en"));
    [zhButton, enButton].forEach((button) => {
        button.addEventListener("keydown", (event) => {
            if (event.key === "ArrowRight" || event.key === "ArrowLeft") {
                event.preventDefault();
                if (button === zhButton) {
                    moveTo("en", enButton);
                }
                else {
                    moveTo("zh", zhButton);
                }
            }
            else if (event.key === "Home") {
                event.preventDefault();
                moveTo("zh", zhButton);
            }
            else if (event.key === "End") {
                event.preventDefault();
                moveTo("en", enButton);
            }
        });
    });
    activate("zh");
    return wrapper;
}

function createVerifierEvidence(verifier, task) {
    const indexed = getIndexedVerifierSource(task);
    const wrapper = createElement("section", "verifier-evidence");
    const head = createElement("div", "verifier-evidence-head");
    head.append(
        createElement("strong", "", "Verifier 实现与依据"),
        createElement("span", "", "内容直接内嵌；外部链接仅保留作溯源"),
    );
    const tabList = createElement("div", "verifier-source-tabs");
    tabList.setAttribute("role", "tablist");
    tabList.setAttribute("aria-label", "Verifier 内容类型");
    const panelWrap = createElement("div", "verifier-source-panels");
    const groupId = `verifier-source-${interactiveId += 1}`;
    const definitions = [
        {kind: "code", label: "源码"},
        {kind: "config", label: "详细配置"},
        {kind: "official", label: "官方说明"},
    ];
    const controls = definitions.map((definition, index) => {
        const spec = normalizeVerifierSourceSpec(definition.kind, verifier, indexed);
        const button = createElement(
            "button",
            `verifier-source-tab${index === 0 ? " active" : ""}`,
            definition.label,
        );
        const panel = createElement(
            "div",
            `verifier-source-panel${index === 0 ? " active" : ""}`,
        );
        const tabId = `${groupId}-${definition.kind}-tab`;
        const panelId = `${groupId}-${definition.kind}-panel`;
        button.type = "button";
        button.id = tabId;
        button.dataset.sourceKind = definition.kind;
        button.setAttribute("role", "tab");
        button.setAttribute("aria-controls", panelId);
        panel.id = panelId;
        panel.setAttribute("role", "tabpanel");
        panel.setAttribute("aria-labelledby", tabId);
        panel.hidden = index !== 0;
        tabList.append(button);
        panelWrap.append(panel);
        return {button, panel, spec, hydrated: false};
    });

    const activate = (control) => {
        controls.forEach((candidate) => {
            const active = candidate === control;
            candidate.button.classList.toggle("active", active);
            candidate.button.setAttribute("aria-selected", String(active));
            candidate.button.tabIndex = active ? 0 : -1;
            candidate.panel.classList.toggle("active", active);
            candidate.panel.hidden = !active;
        });
        if (!control.hydrated) {
            control.hydrated = true;
            void hydrateVerifierSourcePanel(control.panel, control.spec);
        }
    };
    controls.forEach((control) => {
        control.button.addEventListener("click", () => activate(control));
        control.button.addEventListener("keydown", (event) => {
            if (!["ArrowLeft", "ArrowRight"].includes(event.key)) {
                return;
            }
            event.preventDefault();
            const currentIndex = controls.indexOf(control);
            const step = event.key === "ArrowRight" ? 1 : -1;
            const next = controls[(currentIndex + step + controls.length) % controls.length];
            activate(next);
            next.button.focus();
        });
    });
    wrapper.append(head, tabList, panelWrap);
    activate(controls[0]);
    return wrapper;
}

async function hydrateVerifierSourcePanel(panel, spec) {
    panel.replaceChildren();
    if (!state.assetIndexesLoaded) {
        panel.append(createElement("div", "source-loading", "正在索引本站收录的 Verifier 内容…"));
        return;
    }
    let content = spec.content;
    let loadError = "";
    if (!content && spec.url && isLocalUrl(spec.url)) {
        const loading = createElement("div", "source-loading", "正在读取本站收录内容…");
        panel.append(loading);
        try {
            content = await fetchVerifierText(spec.url);
        }
        catch (error) {
            loadError = error?.message || "读取失败";
        }
        panel.replaceChildren();
    }

    if (!content) {
        const empty = createElement("div", "source-empty-state");
        empty.append(
            createElement("strong", "", spec.emptyTitle),
            createElement(
                "p",
                "",
                loadError
                    ? `本站内容读取失败：${loadError}。外部地址仍仅作为溯源入口。`
                    : spec.emptyDescription,
            ),
        );
        if (safeHttpUrl(spec.originUrl)) {
            empty.append(createExternalLink("打开官方原文 ↗", spec.originUrl, "source-origin-link"));
        }
        panel.append(empty);
        return;
    }

    const toolbar = createElement("div", "source-content-toolbar");
    const meta = createElement("span", "", spec.label);
    const copyButton = createElement("button", "source-copy-button", "复制内容");
    copyButton.type = "button";
    copyButton.addEventListener("click", async () => {
        const copied = await copyPlainText(content);
        copyButton.textContent = copied ? "已复制" : "复制失败";
        window.setTimeout(() => {
            copyButton.textContent = "复制内容";
        }, 1400);
    });
    toolbar.append(meta, copyButton);

    const explanation = createElement(
        "div",
        `source-zh-explanation${spec.explanationZh ? "" : " source-translation-missing"}`,
    );
    explanation.append(
        createElement("strong", "", spec.explanationZh ? "中文辅助理解" : "中文辅助说明待补"),
        createElement(
            "p",
            "",
            spec.explanationZh
                || (
                    "当前先原样展示官方内容；"
                    + "本站尚未收录与相应代码或配置片段对应的中文说明。"
                ),
        ),
    );
    const pre = createElement("pre", `verifier-source-code language-${spec.language}`);
    const code = createElement("code", "", content);
    pre.append(code);
    panel.append(toolbar, explanation, pre);
    if (safeHttpUrl(spec.originUrl)) {
        panel.append(createExternalLink("查看官方出处 ↗", spec.originUrl, "source-origin-link"));
    }
}

function normalizeVerifierSourceSpec(kind, verifier, indexed) {
    const kindSources = [
        indexed?.sources?.[kind],
        indexed?.inline?.[kind],
        indexed?.[kind],
        indexed?.verifier?.[kind],
        verifier?.sources?.[kind],
        verifier?.inline?.[kind],
    ].filter(Boolean);
    const objectSource = kindSources.find((value) => value && typeof value === "object") || {};
    const definitions = {
        code: {
            label: "Verifier 源码 · 原始文件",
            fields: ["content", "text", "body", "source_code", "code_content", "verifier_code", "code"],
            url: firstString(objectSource.url, indexed?.code_url, verifier?.code_url),
            explanation: ["code_explanation_zh", "source_code_explanation_zh"],
            emptyTitle: "尚未收录可直接展示的 Verifier 源码",
            emptyDescription: (
                "这里只有源码地址或评测协议，不能把一个跳转链接冒充源码正文。"
            ),
        },
        config: {
            label: "详细配置 · 原始文件",
            fields: [
                "content", "text", "body", "config_content", "detailed_config",
                "configuration", "config", "rubric_pretty",
            ],
            url: firstString(objectSource.url, indexed?.config_url, verifier?.config_url),
            explanation: ["config_explanation_zh", "configuration_explanation_zh"],
            emptyTitle: "尚未收录可直接展示的详细配置",
            emptyDescription: (
                "当前没有站内配置正文；公开镜像补齐后会在此显示，而不是只给出跳转按钮。"
            ),
        },
        official: {
            label: "官方说明 · 原始文件",
            fields: [
                "content", "text", "body", "official_content",
                "documentation", "official_notes", "source_content",
            ],
            url: firstString(objectSource.url, indexed?.source_url, verifier?.source_url),
            explanation: ["official_explanation_zh", "documentation_zh"],
            emptyTitle: "尚未收录可直接展示的官方说明正文",
            emptyDescription: "官方来源仍可用于溯源，但本站还没有可内嵌的说明文本。",
        },
    };
    const definition = definitions[kind];
    const sourceValues = [objectSource, indexed, indexed?.verifier, verifier];
    let rawContent = "";
    sourceValues.some((source) => definition.fields.some((field) => {
        const value = source?.[field];
        if (value === undefined || value === null || value === "") {
            return false;
        }
        rawContent = value;
        return true;
    }));
    if (!rawContent && typeof kindSources[0] === "string" && !looksLikeUrl(kindSources[0])) {
        rawContent = kindSources[0];
    }
    const content = stringifyVerifierContent(rawContent);
    const explanationFields = [
        ...definition.explanation,
        "explanation_zh",
        "commentary_zh",
        "translation_zh",
    ];
    let explanationZh = "";
    [objectSource, indexed?.[kind], indexed, verifier].some((source) => explanationFields.some((field) => {
        const value = source?.[field];
        if (typeof value !== "string" || !value.trim()) {
            return false;
        }
        explanationZh = value.trim();
        return true;
    }));
    return {
        content,
        url: definition.url,
        originUrl: firstString(
            objectSource.official_url,
            objectSource.source_url,
            indexed?.sources?.[kind]?.official_url,
            indexed?.sources?.[kind]?.source_url,
            !isLocalUrl(definition.url) ? definition.url : "",
        ),
        explanationZh,
        label: definition.label,
        emptyTitle: definition.emptyTitle,
        emptyDescription: definition.emptyDescription,
        language: inferSourceLanguage(definition.url, kind, objectSource.language),
    };
}

function getIndexedVerifierSource(task) {
    const taskId = normalizeIdentity(task?.id);
    const benchId = normalizeIdentity(state.activeBenchId);
    return state.verifierSourcesByTask.get(`${benchId}::${taskId}`)
        || state.verifierSourcesByTask.get(`::${taskId}`)
        || null;
}

function stringifyVerifierContent(value) {
    if (typeof value === "string") {
        return value.trim();
    }
    if (value && typeof value === "object") {
        const nested = firstString(value.content, value.text, value.body, value.source);
        if (nested) {
            return nested;
        }
        try {
            return JSON.stringify(value, null, 2);
        }
        catch (_error) {
            return String(value);
        }
    }
    return "";
}

function inferSourceLanguage(url, kind, declared) {
    if (declared) {
        return String(declared).toLocaleLowerCase().replace(/[^a-z0-9_-]/g, "");
    }
    const extension = fileExtension(url);
    if (extension) {
        return extension;
    }
    return kind === "code" ? "text" : kind;
}

async function fetchVerifierText(url) {
    const resolved = safeHttpUrl(url);
    if (!resolved || !isLocalUrl(resolved)) {
        throw new Error("只允许读取本站内容");
    }
    if (verifierTextCache.has(resolved)) {
        return verifierTextCache.get(resolved);
    }
    const pending = fetch(resolved, {credentials: "same-origin"}).then((response) => {
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        return response.text();
    });
    verifierTextCache.set(resolved, pending);
    try {
        return await pending;
    }
    catch (error) {
        verifierTextCache.delete(resolved);
        throw error;
    }
}

async function copyPlainText(text) {
    try {
        await navigator.clipboard.writeText(text);
        return true;
    }
    catch (_error) {
        const textarea = document.createElement("textarea");
        textarea.value = text;
        textarea.setAttribute("readonly", "");
        textarea.style.position = "fixed";
        textarea.style.opacity = "0";
        document.body.append(textarea);
        textarea.select();
        const copied = document.execCommand("copy");
        textarea.remove();
        return copied;
    }
}

function createInspectorSection(kicker, title) {
    const section = createElement("section", "inspector-section");
    const titleRow = createElement("div", "inspector-section-title");
    titleRow.append(createElement("h3", "", title), createElement("span", "", kicker));
    const body = document.createElement("div");
    section.append(titleRow, body);
    return {section, titleRow, body};
}

function normalizeInputMaterials(task) {
    const source = task.raw?.source || task.raw?.input || {};
    const files = asArray(source?.files || source?.inputs || task.raw?.input_files);
    const rawMaterials = files.length ? files : (hasFileSignal(source) ? [source] : []);
    return rawMaterials.map((item, index) => normalizeMaterial(item, `输入 ${index + 1}`));
}

function normalizeOutputMaterials(task) {
    const artifact = task.raw?.artifact || task.raw?.output || {};
    const files = asArray(artifact?.files || artifact?.outputs || task.raw?.output_files);
    const rawMaterials = files.length ? files : (hasFileSignal(artifact) ? [artifact] : []);
    return rawMaterials.map((item, index) => normalizeMaterial(item, `产物 ${index + 1}`));
}

function mergeIndexedMaterials(declaredMaterials, task, slot) {
    const previewRecords = state.previewRecordsByBench.get(state.activeBenchId) || [];
    const mirrorRecords = state.mirrorRecordsByBench.get(state.activeBenchId) || [];
    const canonicalTaskId = normalizeIdentity(task.id);
    const indexedByKey = new Map();
    [...mirrorRecords, ...previewRecords].forEach((record) => {
        const taskIds = [
            firstString(record?.task_id, record?.task_key, record?.uid),
            ...asArray(record?.task_ids),
        ].map(normalizeIdentity).filter(Boolean);
        if (!taskIds.includes(canonicalTaskId)
            || !indexedRecordCanSynthesizeMaterial(record, task, slot)) {
            return;
        }
        indexedByKey.set(indexedRecordKey(record), record);
    });

    const matchedKeys = new Set();
    declaredMaterials.forEach((material) => {
        const match = getMaterialIndexMatch(material, task, slot);
        const record = match?._previewRecord || match?._mirrorRecord;
        if (record) {
            matchedKeys.add(indexedRecordKey(record));
        }
    });

    const merged = [...declaredMaterials];
    indexedByKey.forEach((record, key) => {
        if (matchedKeys.has(key)) {
            return;
        }
        const logicalPath = firstString(
            record?.logical_path,
            record?.repository_path,
            record?.archive_member,
            record?.view_path,
        );
        const filename = firstString(record?.filename, logicalPath.split("/").pop());
        merged.push(normalizeMaterial(
            {
                filename,
                path: logicalPath,
                repository_path: record?.repository_path,
                archive_member: record?.archive_member,
                url: firstString(record?.source_url, record?.url),
                role: firstString(record?.role, record?.slot, record?.type),
                status: record?.status,
            },
            slot === "input" ? "镜像输入" : "镜像产物",
        ));
    });
    return merged;
}

function indexedRecordCanSynthesizeMaterial(record, task, slot) {
    const role = firstString(record?.role, record?.slot, record?.type).toLocaleLowerCase();
    const status = firstString(record?.status).toLocaleLowerCase();
    if (!role || ["error", "skipped"].includes(status)) {
        return false;
    }
    if (!mirrorRecordMatchesContext(record, task, slot)) {
        return false;
    }
    if (slot !== "output" || !["gold", "reference"].includes(role)) {
        return true;
    }
    const artifactStatus = firstString(task?.raw?.artifact?.status).toLocaleLowerCase();
    return artifactStatus !== "not_published";
}

function indexedRecordKey(record) {
    return [
        firstString(record?.role, record?.slot, record?.type),
        firstString(
            record?.logical_path,
            record?.repository_path,
            record?.archive_member,
            record?.view_path,
            record?.preview_url,
            record?.sha256,
        ),
    ].map(normalizeIdentity).join("::");
}

function normalizeMaterial(item, fallbackName) {
    const rawItem = typeof item === "string" ? {filename: item} : (item || {});
    const declaredName = firstString(
        rawItem.filename,
        rawItem.name,
        rawItem.title,
        rawItem.path,
    );
    const filename = declaredName || fallbackName;
    const format = firstString(rawItem.format, fileExtension(filename), rawItem.kind).toLocaleLowerCase();
    return {
        raw: rawItem,
        name: filename,
        isFallbackName: !declaredName,
        isHumanReference: /accepted[_ -]human[_ -]deliverable|human[_ -]reference/.test(
            firstString(rawItem.role, rawItem.status).toLocaleLowerCase(),
        ),
        format: format.toUpperCase().slice(0, 12),
        formatKey: format,
        availability: firstString(rawItem.availability, rawItem.status, "tracked"),
        note: firstString(rawItem.note, rawItem.description),
        url: firstString(rawItem.local_url, rawItem.mirror_url, rawItem.url, rawItem.source_url),
    };
}

function resolvePreviewSpec(material, task, slot) {
    const raw = material.raw || {};
    const match = getMaterialIndexMatch(material, task, slot);
    const previewRecord = match?._previewRecord || null;
    const mirrorRecord = match?._mirrorRecord || null;
    const legacyRecord = match?._legacyRecord || null;
    const previewObjects = [
        previewRecord,
        legacyRecord,
        legacyRecord?.preview,
        raw,
        raw?.preview,
        ...(slot === "output" ? [task.raw?.preview] : []),
    ].filter(Boolean);
    let pageImages = uniqueStrings(previewObjects.flatMap((item) => {
        return asArray(item?.page_images || item?.pages || item?.preview_pages)
            .map((page) => firstString(page?.local_url, page?.url, page?.path, page));
    })).map(resolvePreviewAssetUrl).filter(isLocalUrl);
    let textChunks = previewObjects.flatMap((item) => asArray(item?.text_chunks || item?.chunks));
    const htmlBundle = previewRecord?.safe_html_bundle;
    const htmlUrl = typeof htmlBundle === "string"
        ? htmlBundle
        : firstString(
            previewRecord?.preview_kind === "html" ? previewRecord?.preview_url : "",
            htmlBundle?.entry_url,
            htmlBundle?.local_url,
            htmlBundle?.url,
            htmlBundle?.path,
        );
    const sanitizedHtmlUrl = resolvePreviewAssetUrl(htmlUrl);
    const sanitizedHtml = Boolean(
        previewRecord
        && previewRecord.preview_kind === "html"
        && previewRecord.security_profile === TRUSTED_HTML_SECURITY_PROFILE
        && sanitizedHtmlUrl
        && isLocalUrl(sanitizedHtmlUrl)
        && isTrustedHtmlPreviewPath(sanitizedHtmlUrl),
    );
    const spreadsheetManifestUrl = resolvePreviewAssetUrl(firstString(
        previewRecord?.spreadsheet_manifest_url,
        previewRecord?.sheet_manifest_url,
        previewRecord?.preview_kind === "spreadsheet_static" ? previewRecord?.preview_url : "",
    ));
    const spreadsheetPrintViewUrl = resolvePreviewAssetUrl(firstString(
        previewRecord?.print_view_url,
        previewRecord?.printViewUrl,
    ));
    const trustedSpreadsheet = Boolean(
        previewRecord
        && previewRecord.preview_kind === "spreadsheet_static"
        && previewRecord.security_profile === TRUSTED_SPREADSHEET_SECURITY_PROFILE
        && isTrustedSpreadsheetPreviewPath(spreadsheetManifestUrl)
    );
    const mirrorUrl = resolvePreviewAssetUrl(firstString(
        mirrorRecord?.view_path,
        mirrorRecord?.local_url,
        mirrorRecord?.mirror_url,
        mirrorRecord?.object_path,
    ));
    const localCandidates = previewObjects.flatMap((item) => [
        item?.local_preview_url,
        item?.local_url,
        item?.mirror_url,
        item?.preview_url,
        item?.entry_url,
        item?.path,
        item?.url,
    ]).filter(Boolean);
    if (mirrorUrl) {
        localCandidates.push(mirrorUrl);
    }
    let localUrl = [
        trustedSpreadsheet ? spreadsheetManifestUrl : "",
        sanitizedHtml ? sanitizedHtmlUrl : "",
        ...localCandidates,
    ]
        .map(resolvePreviewAssetUrl)
        .find((url) => isLocalUrl(url)) || "";
    const externalUrl = [
        raw?.source_url,
        raw?.original_url,
        raw?.official_url,
        material.url,
        mirrorRecord?.url,
        mirrorRecord?.source_url,
        legacyRecord?.source_url,
        legacyRecord?.original_url,
        ...localCandidates,
    ].find((url) => safeHttpUrl(url) && !isLocalUrl(url)) || "";
    const declaredKind = firstString(
        previewRecord?.preview_kind,
        legacyRecord?.preview_kind,
        legacyRecord?.kind,
        raw?.preview_kind,
        raw?.preview?.preview_kind,
        task.raw?.preview?.preview_kind,
    ).toLocaleLowerCase();
    if (declaredKind === "spreadsheet_static" && !trustedSpreadsheet) {
        localUrl = "";
    }
    const previewState = firstString(
        previewRecord?.preview_state,
        previewRecord?.preview_kind,
        previewRecord?.status,
    ).toLocaleLowerCase();
    const protectedMirrored = Boolean(
        mirrorRecord?.status === "ready"
        && mirrorRecord?.storage_class === "protected_corpus"
    );
    const indexedPublicPreviewUrl = [
        previewRecord?.local_preview_url,
        previewRecord?.local_url,
        previewRecord?.preview_url,
        previewRecord?.entry_url,
        previewRecord?.path,
        previewRecord?.url,
    ].map(resolvePreviewAssetUrl).find((url) => isLocalUrl(url)) || "";
    const protectedWithoutPublicPreview = Boolean(
        protectedMirrored
        && !indexedPublicPreviewUrl
        && !pageImages.length
        && !textChunks.length
        && !sanitizedHtml
    );
    if (protectedWithoutPublicPreview) {
        localUrl = "";
        pageImages = [];
        textChunks = [];
    }
    const localExtension = fileExtension(localUrl);
    let kind = "missing";
    if (pageImages.length) {
        kind = "pages";
    }
    else if (trustedSpreadsheet) {
        kind = "spreadsheet";
    }
    else if (sanitizedHtml) {
        kind = "html";
    }
    else if (textChunks.length) {
        kind = "text";
    }
    else if (localUrl) {
        if (declaredKind.includes("html") || ["html", "htm"].includes(localExtension)) {
            kind = sanitizedHtml ? "html" : "missing";
        }
        else if (declaredKind.includes("pdf") || localExtension === "pdf") {
            kind = "pdf";
        }
        else if (declaredKind.includes("text") || ["json", "jsonl", "txt", "md", "csv"].includes(localExtension)) {
            kind = "text";
        }
        else if (declaredKind.includes("image") || ["png", "jpg", "jpeg", "webp", "gif", "svg"].includes(localExtension)) {
            kind = "image";
        }
    }
    return {
        kind,
        localUrl,
        externalUrl,
        pageImages,
        textChunks,
        spreadsheetManifestUrl: trustedSpreadsheet ? spreadsheetManifestUrl : "",
        printViewUrl: trustedSpreadsheet && isTrustedSpreadsheetPrintViewPath(spreadsheetPrintViewUrl)
            ? spreadsheetPrintViewUrl
            : "",
        sourceSha256: firstString(previewRecord?.source_sha256, mirrorRecord?.sha256),
        integrityStatus: firstString(
            previewRecord?.integrity_status,
            mirrorRecord?.integrity_status,
            raw?.integrity_status,
        ),
        integrityNote: firstString(
            previewRecord?.integrity_note_zh,
            mirrorRecord?.integrity_note_zh,
            raw?.integrity_note_zh,
        ),
        sanitizedHtml,
        iframeSandbox: sanitizeIframeSandbox(previewRecord?.iframe_sandbox),
        mirrorReady: Boolean(mirrorRecord && mirrorUrl && mirrorRecord.status !== "error"),
        protectedMirrored,
        previewState,
        mirrorUrl: isLocalUrl(mirrorUrl) ? mirrorUrl : "",
        mirrorBound: Boolean(mirrorRecord),
        previewBound: Boolean(previewRecord),
        indexesLoaded: state.assetIndexesLoaded,
        benchHasIndexedAssets: Boolean(
            state.mirrorRecordsByBench.get(state.activeBenchId)?.length
            || state.previewRecordsByBench.get(state.activeBenchId)?.length,
        ),
        provenanceLabel: formatIndexedProvenance(
            previewRecord || mirrorRecord,
            material,
            slot,
        ),
    };
}

function getMaterialIndexMatch(material, task, slot) {
    if (!Object.prototype.hasOwnProperty.call(material, "_indexMatch")) {
        material._indexMatch = findMirrorEntry(task, material, slot);
    }
    return material._indexMatch;
}

function resolveMaterialProvenance(material, task, slot) {
    const match = getMaterialIndexMatch(material, task, slot);
    return formatIndexedProvenance(
        match?._previewRecord || match?._mirrorRecord,
        material,
        slot,
    );
}

function formatIndexedProvenance(record, material, slot) {
    if (material.isHumanReference) {
        return "官方接受的人类参考产物（非模型产物）";
    }
    const role = firstString(record?.role).toLocaleLowerCase();
    if (role === "candidate") {
        const model = firstString(record?.candidate_model, "官方发布模型");
        return `${model} 官方候选${record?.non_gold === false ? "" : " · 非 Gold"}`;
    }
    if (role === "gold") {
        return "官方参考答案 / Gold";
    }
    if (role === "reference") {
        return "官方参考材料";
    }
    if (role === "input") {
        return "官方输入镜像";
    }
    if (role === "catalog") {
        return slot === "input" ? "官方目录 / 输入材料" : "官方目录记录";
    }
    return "";
}

function findMirrorEntry(task, material, slot) {
    const previewRecords = state.previewRecordsByBench.get(state.activeBenchId) || [];
    const mirrorRecords = state.mirrorRecordsByBench.get(state.activeBenchId) || [];
    const previewRecord = findBestIndexedRecord(previewRecords, task, material, slot);
    let mirrorRecord = findBestIndexedRecord(mirrorRecords, task, material, slot);
    if (previewRecord && !mirrorRecord) {
        mirrorRecord = findCompanionMirrorRecord(mirrorRecords, previewRecord, task, material, slot);
    }
    const materialRole = firstString(material?.raw?.role, material?.raw?.slot).toLocaleLowerCase();
    const strictReference = slot === "output" && ["reference", "source"].includes(materialRole);
    if (strictReference && (!previewRecord || !mirrorRecord)) {
        return null;
    }
    if (previewRecord || mirrorRecord) {
        return {
            _previewRecord: previewRecord,
            _mirrorRecord: mirrorRecord,
            _indexBound: true,
        };
    }

    const legacyRecord = findLegacyMirrorEntry(task, material, slot);
    return legacyRecord ? {_legacyRecord: legacyRecord} : null;
}

function findBestIndexedRecord(records, task, material, slot) {
    let best = null;
    let bestScore = -1;
    records.forEach((record) => {
        const score = scoreIndexedRecord(record, task, material, slot);
        if (score > bestScore) {
            best = record;
            bestScore = score;
        }
    });
    return bestScore >= 40 ? best : null;
}

function scoreIndexedRecord(record, task, material, slot) {
    if (!mirrorRecordMatchesContext(record, task, slot, material)) {
        return -1;
    }
    let score = 0;
    let contextMatched = false;
    let materialIdentityMatched = false;
    let strongMaterialIdentityMatched = false;
    const recordTaskId = firstString(record?.task_id, record?.task_key, record?.uid);
    const canonicalTaskId = normalizeIdentity(task.id);
    const sharedTaskIds = asArray(record?.task_ids).map(normalizeIdentity).filter(Boolean);
    const taskIdMatched = (recordTaskId && normalizeIdentity(recordTaskId) === canonicalTaskId)
        || sharedTaskIds.includes(canonicalTaskId);
    if (taskIdMatched) {
        score += 140;
        contextMatched = true;
    }

    const taskLines = extractTaskSourceLines(task, slot);
    const recordLine = extractRecordSourceLine(record);
    if (recordLine && taskLines.includes(recordLine)) {
        score += 130;
        contextMatched = true;
    }

    const recordPaths = extractRecordPaths(record);
    const materialPaths = extractMaterialPaths(material);
    const pathScore = bestPathMatchScore(materialPaths, recordPaths);
    if (pathScore) {
        score += pathScore;
        materialIdentityMatched = true;
    }
    const strongPathScore = bestPathMatchScore(
        extractStrongMaterialPaths(material),
        extractStrongRecordPaths(record),
    );
    if (strongPathScore) {
        strongMaterialIdentityMatched = true;
    }

    const taskMarker = `/tasks/${normalizePathValue(task.id)}/`;
    if (recordPaths.some((path) => `/${path}/`.includes(taskMarker))) {
        score += 105;
        contextMatched = true;
    }

    const materialUrls = extractMaterialUrls(material);
    const recordUrls = extractRecordUrls(record);
    if (materialUrls.some((url) => recordUrls.includes(url))) {
        score += 110;
        materialIdentityMatched = true;
        strongMaterialIdentityMatched = true;
    }

    const materialName = normalizePathValue(material.name).split("/").pop();
    const recordNames = recordPaths.map((path) => path.split("/").pop());
    if (materialName && recordNames.includes(materialName)) {
        score += 48;
        materialIdentityMatched = true;
    }

    const taskSourceUrls = extractTaskSourceUrls(task, slot);
    const recordSourceUrls = extractRecordUrls(record);
    if (taskSourceUrls.some((url) => recordSourceUrls.includes(url))) {
        score += 64;
        contextMatched = true;
    }

    const role = firstString(record?.role, record?.slot, record?.type).toLocaleLowerCase();
    const artifactStatus = firstString(task.raw?.artifact?.status).toLocaleLowerCase();
    if (slot === "output"
        && artifactStatus === "not_published"
        && ["gold", "reference"].includes(role)) {
        return -1;
    }
    if (slot === "output" && ["gold", "reference"].includes(role) && !materialIdentityMatched) {
        return -1;
    }
    if ((slot === "input" && role === "input") || (slot === "output" && role === "candidate")) {
        score += 12;
    }
    const declaredMaterialCount = slot === "input"
        ? normalizeInputMaterials(task).length
        : normalizeOutputMaterials(task).length;
    if (declaredMaterialCount > 1 && !materialIdentityMatched) {
        return -1;
    }
    if (!contextMatched && !strongMaterialIdentityMatched) {
        return -1;
    }
    return score;
}

function findCompanionMirrorRecord(records, previewRecord, task, material, slot) {
    const sourceHash = firstString(previewRecord?.source_sha256, previewRecord?.sha256);
    const logicalPath = normalizePathValue(previewRecord?.logical_path);
    const role = firstString(previewRecord?.role, previewRecord?.slot).toLocaleLowerCase();
    const strictReference = slot === "output" && ["reference", "source"].includes(role);
    return records.find((record) => {
        const recordHash = firstString(record?.sha256, record?.source_sha256);
        const recordPath = normalizePathValue(record?.logical_path);
        if (strictReference) {
            return mirrorRecordMatchesContext(record, task, slot, material)
                && Boolean(sourceHash && recordHash === sourceHash && logicalPath && recordPath === logicalPath);
        }
        return (sourceHash && recordHash === sourceHash) || (logicalPath && recordPath === logicalPath);
    }) || null;
}

function findLegacyMirrorEntry(task, material, slot) {
    const manifests = [state.benchMirrorManifest, state.globalMirrorManifest].filter(Boolean);
    for (const manifest of manifests) {
        const benchmarkCollection = manifest?.benchmarks;
        const benchmarkFromArray = Array.isArray(benchmarkCollection)
            ? benchmarkCollection.find((bench) => bench?.id === state.activeBenchId)
            : null;
        const benchNode = manifest?.benches?.[state.activeBenchId]
            || benchmarkFromArray
            || (!Array.isArray(benchmarkCollection) ? benchmarkCollection?.[state.activeBenchId] : null)
            || manifest?.[state.activeBenchId]
            || manifest;
        const taskNode = benchNode?.tasks?.[task.id]
            || benchNode?.items?.[task.id]
            || benchNode?.records?.[task.id]
            || benchNode?.[task.id]
            || manifest?.tasks?.[`${state.activeBenchId}/${task.id}`]
            || manifest?.tasks?.[task.id];
        const slotValues = slot === "input"
            ? [taskNode?.input, taskNode?.inputs, taskNode?.source, taskNode?.sources]
            : [taskNode?.output, taskNode?.outputs, taskNode?.artifact, taskNode?.artifacts];
        const entries = slotValues.flatMap(asArray).filter(Boolean);
        const match = entries.find((entry) => materialMatches(entry, material));
        if (match) {
            return match;
        }
        if (entries.length === 1 && legacySingletonIsSafe(entries[0], material, slot)) {
            return entries[0];
        }
        const fileMap = taskNode?.files || benchNode?.files || manifest?.files || {};
        if (!Array.isArray(fileMap) && typeof fileMap === "object") {
            const direct = fileMap[material.name] || fileMap[material.raw?.id] || fileMap[material.url];
            if (direct) {
                return direct;
            }
        }
        const fileMatch = asArray(fileMap).find((entry) => materialMatches(entry, material));
        if (fileMatch) {
            return fileMatch;
        }
        const indexedRecords = [
            ...asArray(taskNode?.assets),
            ...asArray(taskNode?.records),
            ...asArray(benchNode?.assets),
            ...asArray(benchNode?.records),
            ...asArray(manifest?.assets),
            ...asArray(manifest?.records),
        ].filter((entry) => mirrorRecordMatchesContext(entry, task, slot));
        const indexedMatch = indexedRecords.find((entry) => materialMatches(entry, material));
        if (indexedMatch) {
            return indexedMatch;
        }
        if (indexedRecords.length === 1 && legacySingletonIsSafe(indexedRecords[0], material, slot)) {
            return indexedRecords[0];
        }
    }
    return null;
}

function legacySingletonIsSafe(record, material, slot) {
    const role = firstString(record?.role, record?.slot, record?.type).toLocaleLowerCase();
    if (slot === "output" && ["gold", "reference"].includes(role)) {
        return materialMatches(record, material);
    }
    return true;
}

function mirrorRecordMatchesContext(entry, task, slot, material = null) {
    const benchId = firstString(entry?.bench_id, entry?.benchmark_id, entry?.bench);
    if (benchId && benchId !== state.activeBenchId) {
        return false;
    }
    // Some generated indexes use asset IDs rather than canonical shard task IDs.
    // An exact task ID earns a high score, while reliable source-line/path matches
    // remain eligible when the index ID uses a different namespace.
    const role = firstString(entry?.role, entry?.slot, entry?.type).toLocaleLowerCase();
    if (!role) {
        return true;
    }
    const inputRoles = new Set(["input", "source", "reference", "context", "catalog"]);
    const outputRoles = new Set(["output", "artifact", "gold", "candidate", "deliverable"]);
    if (slot === "output" && ["reference", "source"].includes(role)) {
        return isAcceptedHumanDeliverable(material, task)
            || strictReferenceRecordMatchesContext(entry, task, material);
    }
    return slot === "input" ? inputRoles.has(role) : outputRoles.has(role);
}

function strictReferenceRecordMatchesContext(entry, task, material) {
    const status = firstString(entry?.status).toLocaleLowerCase();
    if (status !== "ready" || !material) {
        return false;
    }
    const canonicalTaskId = normalizeIdentity(task?.id);
    const recordTaskId = normalizeIdentity(firstString(entry?.task_id, entry?.task_key, entry?.uid));
    const sharedTaskIds = asArray(entry?.task_ids).map(normalizeIdentity).filter(Boolean);
    if (!canonicalTaskId || (recordTaskId !== canonicalTaskId && !sharedTaskIds.includes(canonicalTaskId))) {
        return false;
    }
    const materialPaths = extractStrongMaterialPaths(material);
    const recordPaths = extractStrongRecordPaths(entry);
    const pathMatched = materialPaths.some((path) => recordPaths.includes(path));
    const materialHash = firstString(material?.raw?.sha256, material?.raw?.source_sha256);
    const recordHash = firstString(entry?.source_sha256, entry?.sha256);
    return Boolean(pathMatched && materialHash && recordHash === materialHash);
}

function isAcceptedHumanDeliverable(material, task) {
    const evidence = [
        material?.raw?.role,
        material?.raw?.status,
        task?.raw?.artifact?.status,
        task?.raw?.artifact?.role,
    ].join(" ").toLocaleLowerCase();
    return /accepted[_ -]human[_ -]deliverable|human[_ -]reference/.test(evidence);
}

function extractTaskSourceLines(task, slot) {
    const nodes = slot === "input"
        ? [task.raw?.source, task.raw?.input, task.raw]
        : [task.raw?.artifact, task.raw?.output, task.raw];
    return [...new Set(nodes.flatMap((node) => [
        Number(node?.source_line),
        extractLineNumber(node?.source_url),
        extractLineNumber(node?.url),
    ]).filter((value) => Number.isInteger(value) && value > 0))];
}

function extractRecordSourceLine(record) {
    const explicit = Number(record?.source_line);
    if (Number.isInteger(explicit) && explicit > 0) {
        return explicit;
    }
    return extractLineNumber(firstString(
        record?.source_url,
        record?.url,
        record?.logical_path,
        record?.source_view_path,
    ));
}

function extractLineNumber(value) {
    const text = String(value || "");
    const lineMatch = text.match(/#L0*(\d+)(?:\D|$)/i);
    if (lineMatch) {
        return Number(lineMatch[1]);
    }
    const taskMatch = text.match(/(?:^|[/_-])task[-_]0*(\d+)(?:\D|$)/i);
    return taskMatch ? Number(taskMatch[1]) : 0;
}

function extractRecordPaths(record) {
    return uniqueStrings([
        record?.repository_path,
        record?.archive_member,
        record?.logical_path,
        record?.view_path,
        record?.source_view_path,
        record?.filename,
        record?.name,
    ]).map(normalizePathValue).filter(Boolean);
}

function extractMaterialPaths(material) {
    const raw = material.raw || {};
    return uniqueStrings([
        raw.repository_path,
        raw.archive_path,
        raw.archive_member,
        raw.logical_path,
        raw.path,
        raw.filename,
        raw.name,
        material.name,
    ]).map(normalizePathValue).filter(Boolean);
}

function extractStrongRecordPaths(record) {
    return uniqueStrings([
        record?.repository_path,
        record?.archive_member,
        record?.logical_path,
        record?.source_view_path,
    ]).map(normalizePathValue).filter(Boolean);
}

function extractStrongMaterialPaths(material) {
    const raw = material.raw || {};
    return uniqueStrings([
        raw.repository_path,
        raw.archive_path,
        raw.archive_member,
        raw.logical_path,
        raw.path,
    ]).map(normalizePathValue).filter(Boolean);
}

function bestPathMatchScore(materialPaths, recordPaths) {
    let best = 0;
    materialPaths.forEach((materialPath) => {
        recordPaths.forEach((recordPath) => {
            if (materialPath === recordPath) {
                best = Math.max(best, 124);
                return;
            }
            if (recordPath.endsWith(`/${materialPath}`) || materialPath.endsWith(`/${recordPath}`)) {
                best = Math.max(best, 102);
            }
        });
    });
    return best;
}

function extractMaterialUrls(material) {
    const raw = material.raw || {};
    return uniqueStrings([
        material.url,
        raw.url,
        raw.source_url,
        raw.original_url,
    ]).map(normalizeUrlValue).filter(Boolean);
}

function extractRecordUrls(record) {
    return uniqueStrings([
        record?.url,
        record?.source_url,
        record?.original_url,
    ]).map(normalizeUrlValue).filter(Boolean);
}

function extractTaskSourceUrls(task, slot) {
    const node = slot === "input" ? task.raw?.source : task.raw?.artifact;
    return uniqueStrings([
        node?.source_url,
        node?.url,
    ]).map(normalizeUrlValue).filter(Boolean);
}

function normalizeIdentity(value) {
    return String(value || "").trim().toLocaleLowerCase();
}

function extractExactPromptTranslation(raw) {
    const direct = firstString(
        raw?.task_prompt_zh_exact,
        raw?.prompt_zh_exact,
        raw?.instruction_zh_exact,
        raw?.question_zh_exact,
        raw?.translation_zh_exact,
    );
    const declaredStatus = firstString(raw?.translation_status, raw?.task_prompt_zh_status);
    const nativeChinese = /^zh(?:-|$)/i.test(firstString(raw?.original_language))
        || /^(?:not_required_native_zh|native_zh)$/i.test(declaredStatus);
    if (nativeChinese) {
        return {
            text: firstString(
                direct,
                raw?.task_prompt_zh,
                raw?.prompt_zh,
                raw?.instruction_zh,
                raw?.task_prompt,
                raw?.prompt,
                raw?.instruction,
                raw?.question,
            ),
            status: declaredStatus || "not_required_native_zh",
            isMachine: false,
        };
    }
    if (direct) {
        const status = declaredStatus;
        if (!isExactTranslationStatus(status)) {
            return {text: "", status: status || "missing", isMachine: false};
        }
        const method = firstString(raw?.translation_method, raw?.task_prompt_translation_method);
        return {
            text: direct,
            status,
            isMachine: status.toLocaleLowerCase().includes("machine")
                || method.toLocaleLowerCase().includes("machine"),
        };
    }
    const candidates = [
        raw?.translations?.zh,
        raw?.translations?.["zh-CN"],
        raw?.translation?.zh,
        raw?.task_prompt_translation?.zh,
    ];
    for (const candidate of candidates) {
        const translation = normalizeExactTranslation(candidate);
        if (translation.text) {
            return translation;
        }
    }
    const legacyStatus = firstString(raw?.task_prompt_zh_status, raw?.translation_status);
    if (isExactTranslationStatus(legacyStatus)) {
        const text = firstString(raw?.task_prompt_zh, raw?.prompt_zh, raw?.instruction_zh);
        return {
            text,
            status: legacyStatus,
            isMachine: legacyStatus.toLocaleLowerCase().includes("machine"),
        };
    }
    return {text: "", status: "missing", isMachine: false};
}

function extractExactTitleTranslation(raw) {
    const direct = [raw?.title_zh_exact, raw?.name_zh_exact]
        .map((value) => firstString(value))
        .find((value) => hasMeaningfulChinese(value));
    if (direct) {
        const status = firstString(raw?.title_translation_status, raw?.translation_status);
        if (!isExactTranslationStatus(status)) {
            return {text: "", status: status || "missing", isMachine: false};
        }
        const method = firstString(raw?.translation_method, raw?.title_translation_method);
        return {
            text: direct,
            status,
            isMachine: status.toLocaleLowerCase().includes("machine")
                || method.toLocaleLowerCase().includes("machine"),
        };
    }
    const candidates = [
        raw?.title_translations?.zh,
        raw?.title_translations?.["zh-CN"],
        raw?.translations?.zh?.title
            ? {text: raw.translations.zh.title, status: raw.translations.zh.status}
            : null,
        raw?.translations?.["zh-CN"]?.title
            ? {text: raw.translations["zh-CN"].title, status: raw.translations["zh-CN"].status}
            : null,
    ];
    for (const candidate of candidates) {
        const translation = normalizeExactTranslation(candidate, raw?.title_translation_status);
        if (translation.text && hasMeaningfulChinese(translation.text)) {
            return translation;
        }
    }
    const legacyStatus = firstString(raw?.title_translation_status, raw?.translation_status);
    const legacy = [raw?.title_zh, raw?.name_zh]
        .map((value) => firstString(value))
        .find((value) => hasMeaningfulChinese(value));
    if (isExactTranslationStatus(legacyStatus) && hasMeaningfulChinese(legacy)) {
        const method = firstString(raw?.translation_method, raw?.title_translation_method);
        return {
            text: legacy,
            status: legacyStatus,
            isMachine: legacyStatus.toLocaleLowerCase().includes("machine")
                || method.toLocaleLowerCase().includes("machine"),
        };
    }
    return {text: "", status: "missing", isMachine: false};
}

function normalizeExactTranslation(candidate, inheritedStatus = "") {
    if (!candidate) {
        return {text: "", status: "missing", isMachine: false};
    }
    if (typeof candidate === "string") {
        if (!isExactTranslationStatus(inheritedStatus)) {
            return {text: "", status: "missing", isMachine: false};
        }
        return {
            text: candidate.trim(),
            status: inheritedStatus,
            isMachine: inheritedStatus.toLocaleLowerCase().includes("machine"),
        };
    }
    const status = firstString(candidate.status, candidate.quality, candidate.type, inheritedStatus);
    if (!isExactTranslationStatus(status)) {
        return {text: "", status: "missing", isMachine: false};
    }
    return {
        text: firstString(candidate.text, candidate.content, candidate.value, candidate.full_text),
        status,
        isMachine: status.toLocaleLowerCase().includes("machine") || candidate.machine === true,
    };
}

function isExactTranslationStatus(status) {
    return /^(?:exact|exact_machine_reviewable|verified_exact|human_exact|full|complete)$/i.test(
        String(status || "").trim(),
    );
}

function hasMeaningfulChinese(value) {
    return (String(value || "").match(/[\u3400-\u9fff]/g) || []).length >= 2;
}

function isPrimarilyChinese(value) {
    const text = String(value || "");
    const chineseCount = (text.match(/[\u3400-\u9fff]/g) || []).length;
    const latinCount = (text.match(/[A-Za-z]/g) || []).length;
    return chineseCount > 0 && (latinCount === 0 || chineseCount >= latinCount * 0.45);
}

function firstSentence(value, maximumLength = 90) {
    const normalized = String(value || "").replace(/\s+/g, " ").trim();
    const sentence = normalized.match(/^.*?[。！？!?](?:\s|$)/u)?.[0]?.trim() || normalized;
    return sentence.length > maximumLength
        ? `${sentence.slice(0, maximumLength).trim()}…`
        : sentence;
}

function normalizePathValue(value) {
    let text = String(value || "").trim();
    if (!text) {
        return "";
    }
    try {
        text = decodeURIComponent(text);
    }
    catch (_error) {
        // Keep the original spelling if a partial escape sequence is present.
    }
    return text
        .replaceAll("\\", "/")
        .replaceAll("::", "/")
        .replace(/^[./]+/, "")
        .replace(/\/{2,}/g, "/")
        .toLocaleLowerCase();
}

function normalizeUrlValue(value) {
    const url = safeHttpUrl(value);
    if (!url) {
        return "";
    }
    try {
        const parsed = new URL(url);
        parsed.hash = "";
        return decodeURIComponent(parsed.href).toLocaleLowerCase();
    }
    catch (_error) {
        return url.split("#")[0].toLocaleLowerCase();
    }
}

function sanitizeIframeSandbox(value) {
    const allowedTokens = new Set(["allow-scripts"]);
    return uniqueStrings(String(value || "").split(/\s+/))
        .filter((token) => allowedTokens.has(token))
        .join(" ");
}

function isTrustedHtmlPreviewPath(value) {
    try {
        const url = new URL(value, document.baseURI);
        return url.origin === location.origin && url.pathname.includes("/assets/previews/html/");
    }
    catch (_error) {
        return false;
    }
}

function isTrustedSpreadsheetPreviewPath(value) {
    try {
        const url = new URL(value, document.baseURI);
        return url.origin === location.origin
            && url.pathname.includes("/assets/previews/spreadsheets/");
    }
    catch (_error) {
        return false;
    }
}

function isTrustedSpreadsheetPrintViewPath(value) {
    try {
        const url = new URL(value, document.baseURI);
        return url.origin === location.origin
            && url.pathname.includes("/assets/previews/")
            && url.pathname.toLowerCase().endsWith(".pdf");
    }
    catch (_error) {
        return false;
    }
}

function materialMatches(entry, material) {
    const names = [entry?.filename, entry?.name, entry?.id, entry?.original_url, entry?.source_url]
        .filter(Boolean)
        .map(String);
    return names.includes(material.name)
        || names.includes(String(material.raw?.id || ""))
        || names.includes(material.url);
}

function hasFileSignal(value) {
    return Boolean(value && (
        value.filename || value.name || value.url || value.source_url || value.archive_path
        || value.local_url || value.preview_url || value.preview || value.note || value.status
    ));
}

async function fetchJsonWithProgress(url, onProgress, signal) {
    const response = await fetch(url, {cache: "no-store", signal});
    if (!response.ok) {
        throw new Error(`${url} · HTTP ${response.status}`);
    }
    if (!response.body?.getReader) {
        onProgress({loaded: 0, total: 0, percent: 82, indeterminate: true, stage: "解析 JSON"});
        return response.json();
    }
    const reader = response.body.getReader();
    const encoded = Boolean(response.headers.get("Content-Encoding"));
    const total = encoded ? 0 : Number(response.headers.get("Content-Length")) || 0;
    let preallocated = total ? new Uint8Array(total) : null;
    let chunks = preallocated ? null : [];
    let loaded = 0;
    while (true) {
        const {done, value} = await reader.read();
        if (done) {
            break;
        }
        if (preallocated && loaded + value.length <= preallocated.length) {
            preallocated.set(value, loaded);
        }
        else {
            if (preallocated) {
                chunks = [preallocated.subarray(0, loaded)];
                preallocated = null;
            }
            chunks.push(value);
        }
        loaded += value.length;
        const percent = total ? Math.min(88, Math.max(3, (loaded / total) * 88)) : 0;
        onProgress({loaded, total, percent, indeterminate: !total, stage: "传输"});
    }
    onProgress({loaded, total, percent: 94, indeterminate: false, stage: "解析 JSON"});
    let bytes = preallocated
        ? preallocated.subarray(0, loaded)
        : concatUint8Arrays(chunks, loaded);
    let text = new TextDecoder("utf-8").decode(bytes).replace(/^\uFEFF/, "");
    bytes = null;
    chunks = null;
    preallocated = null;
    const payload = JSON.parse(text);
    text = "";
    return payload;
}

async function fetchJson(url) {
    const response = await fetch(url, {cache: "no-store"});
    if (!response.ok) {
        throw new Error(`${url} · HTTP ${response.status}`);
    }
    return response.json();
}

function concatUint8Arrays(chunks, total) {
    const merged = new Uint8Array(total);
    let offset = 0;
    chunks.forEach((chunk) => {
        merged.set(chunk, offset);
        offset += chunk.length;
    });
    return merged;
}

function showLoader(options) {
    dom.loadingLayer.classList.remove("hidden");
    dom.loadingRetry.classList.add("hidden");
    dom.loadingKicker.textContent = options.kicker || "LOADING";
    dom.loadingTitle.textContent = options.title || "正在读取";
    dom.loadingMessage.textContent = options.message || "请稍候。";
    dom.progressBar.style.width = "4%";
    dom.progressBar.style.background = "";
    dom.progressTrack.classList.add("indeterminate");
    dom.progressValue.textContent = "准备中";
    dom.progressBytes.textContent = "";
}

function updateLoader(options) {
    if (options.message) {
        dom.loadingMessage.textContent = options.message;
    }
    if (Number.isFinite(options.percent)) {
        dom.progressTrack.classList.remove("indeterminate");
        dom.progressBar.style.width = `${Math.min(100, Math.max(3, options.percent))}%`;
        dom.progressValue.textContent = `${Math.round(options.percent)}%`;
    }
    else if (options.indeterminate) {
        dom.progressTrack.classList.add("indeterminate");
    }
}

function updateLoaderProgress(progress, label) {
    dom.loadingMessage.textContent = progress.stage === "解析 JSON"
        ? `${label}已传输完成，正在建立结构…`
        : `${label}正在流式读取；你可以看到真实传输进度。`;
    dom.progressTrack.classList.toggle("indeterminate", progress.indeterminate);
    if (!progress.indeterminate) {
        dom.progressBar.style.width = `${Math.min(100, Math.max(3, progress.percent || 3))}%`;
        dom.progressValue.textContent = progress.total
            ? `${Math.round((progress.loaded / progress.total) * 100)}%`
            : `${Math.round(progress.percent || 0)}%`;
    }
    else {
        dom.progressValue.textContent = progress.loaded ? "持续读取" : "等待响应";
    }
    dom.progressBytes.textContent = progress.loaded
        ? `${formatBytes(progress.loaded)}${progress.total ? ` / ${formatBytes(progress.total)}` : ""}`
        : "";
}

function showLoaderError(title, message, retry) {
    state.retryAction = retry;
    dom.loadingLayer.classList.remove("hidden");
    dom.loadingKicker.textContent = "LOAD INTERRUPTED";
    dom.loadingTitle.textContent = title;
    dom.loadingMessage.textContent = message;
    dom.progressTrack.classList.remove("indeterminate");
    dom.progressBar.style.width = "100%";
    dom.progressBar.style.background = "#c43c42";
    dom.progressValue.textContent = "需要重试";
    dom.progressBytes.textContent = "";
    dom.loadingRetry.classList.remove("hidden");
}

function hideLoader() {
    dom.loadingLayer.classList.add("hidden");
    dom.progressBar.style.background = "";
    state.retryAction = null;
}

function showFatalState(message) {
    dom.catalogHome.classList.add("hidden");
    dom.benchWorkspace.classList.add("hidden");
    dom.fatalState.classList.remove("hidden");
    dom.fatalMessage.textContent = message;
}

function hideFatalState() {
    dom.fatalState.classList.add("hidden");
    if (!state.activeBenchId) {
        dom.catalogHome.classList.remove("hidden");
    }
}

function renderEmptyInspector(title, copy) {
    const placeholder = createElement("div", "inspector-placeholder");
    placeholder.append(
        createElement("span", "placeholder-mark", "EMPTY"),
        createElement("h3", "", title),
        createElement("p", "", copy),
    );
    dom.taskInspector.replaceChildren(placeholder);
}

function showCatalogHome(options = {}) {
    state.activeBenchId = "";
    state.activeTaskId = "";
    state.activeBench = null;
    dom.benchWorkspace.classList.add("hidden");
    dom.catalogHome.classList.remove("hidden");
    markActiveBenchButton();
    if (options.updateLocation !== false) {
        updateLocation("", "");
    }
    setNavStatus("ready", "目录已就绪");
    if (options.scroll !== false) {
        window.scrollTo({top: 0, behavior: "smooth"});
    }
}

function handleHashChange() {
    const params = new URLSearchParams(location.hash.replace(/^#/, ""));
    if (!state.benches.length) {
        return;
    }
    const benchId = params.get("bench") || "";
    const taskId = params.get("task") || "";
    const variant = params.get("variant") || "";
    if (!benchId) {
        showCatalogHome({scroll: false, updateLocation: false});
        return;
    }
    if (benchId && benchId !== state.activeBenchId) {
        void selectBench(benchId, {taskId, variant});
    }
    else if (state.activeBench) {
        const requestedTask = taskId
            ? state.taskViews.find((task) => task.id === taskId)
            : null;
        if (benchId === "officeqa") {
            const nextVariant = officeQaVariantForTask(requestedTask)
                || normalizeOfficeQaVariant(variant)
                || "questions";
            setTaskVariant(nextVariant, {updateLocation: false});
        }
        if (requestedTask && taskId !== state.activeTaskId) {
            selectTask(taskId, {updateLocation: false, scroll: false});
        }
    }
}

function updateLocation(benchId, taskId, variant) {
    const params = new URLSearchParams();
    if (benchId) {
        params.set("bench", benchId);
    }
    if (taskId) {
        params.set("task", taskId);
    }
    const normalizedVariant = normalizeOfficeQaVariant(variant);
    if (benchId === "officeqa" && normalizedVariant) {
        params.set("variant", normalizedVariant);
    }
    const hash = params.toString() ? `#${params.toString()}` : "";
    if (location.hash !== hash) {
        history.replaceState(null, "", `${location.pathname}${location.search}${hash}`);
    }
}

function markActiveBenchButton() {
    dom.benchGroups.querySelectorAll(".bench-button").forEach((button) => {
        const active = button.dataset.benchId === state.activeBenchId;
        button.classList.toggle("active", active);
        button.setAttribute("aria-current", active ? "page" : "false");
    });
}

function setSidebarOpen(open) {
    dom.benchSidebar.classList.toggle("open", open);
    dom.sidebarScrim.classList.toggle("open", open);
    dom.mobileMenuButton.setAttribute("aria-expanded", String(open));
    document.body.style.overflow = open && window.innerWidth <= 960 ? "hidden" : "";
}

function resetBenchFilters() {
    state.benchSearch = "";
    state.relevanceFilter = "";
    state.deliverableFilter = "";
    dom.benchSearch.value = "";
    dom.deliverableFilter.value = "";
    updateRelevanceButtons();
    renderBenchSidebar();
}

function updateRelevanceButtons() {
    dom.relevanceFilters.querySelectorAll("[data-relevance]").forEach((button) => {
        const active = (button.dataset.relevance || "") === state.relevanceFilter;
        button.classList.toggle("active", active);
        button.setAttribute("aria-pressed", String(active));
    });
}

function resetTaskFilters() {
    state.taskSearch = "";
    state.taskCategory = "";
    state.taskDeliverable = "";
    state.taskVariant = state.activeBenchId === "officeqa" ? "questions" : "";
    dom.taskSearch.value = "";
    dom.taskCategoryFilter.value = "";
    dom.taskDeliverableFilter.value = "";
}

function setNavStatus(status, text) {
    dom.navStatusDot.className = `status-dot ${status}`;
    dom.navStatusText.textContent = text;
}

function abortActiveFetch() {
    if (state.fetchController) {
        state.fetchController.abort();
        state.fetchController = null;
    }
}

function getActiveTaskView() {
    return state.taskViews.find((task) => task.id === state.activeTaskId) || null;
}

function extractTasks(value) {
    return asArray(
        value?.tasks || value?.items || value?.records || value?.rows
        || value?.benchmark?.tasks || value?.bench?.tasks,
    );
}

function normalizeDeliverables(values) {
    return uniqueStrings(values.flatMap((value) => {
        const normalized = String(value || "").trim().toLocaleLowerCase();
        if (!normalized) {
            return [];
        }
        if (DELIVERABLE_LABELS.has(normalized)) {
            return [normalized === "other" ? "data_other" : normalized];
        }
        if (FORMAT_TO_DELIVERABLE.has(normalized)) {
            return [FORMAT_TO_DELIVERABLE.get(normalized)];
        }
        if (normalized.includes("powerpoint") || normalized.includes("slide")) {
            return ["presentation"];
        }
        if (normalized.includes("excel") || normalized.includes("sheet") || normalized.includes("workbook")) {
            return ["spreadsheet"];
        }
        if (normalized.includes("word") || normalized.includes("document")) {
            return ["document"];
        }
        if (normalized.includes("html") || normalized.includes("web")) {
            return ["html"];
        }
        if (normalized.includes("pdf")) {
            return ["pdf"];
        }
        if (normalized.includes("image")) {
            return ["image"];
        }
        if (normalized.includes("text") || normalized.includes("answer") || normalized.includes("qa")) {
            return ["text"];
        }
        return ["data_other"];
    }));
}

function applyMirrorPlan(bench) {
    const benchmarks = state.globalMirrorManifest?.benchmarks;
    const plan = Array.isArray(benchmarks)
        ? benchmarks.find((item) => item?.id === bench.id)
        : benchmarks?.[bench.id];
    const mirrorCount = assetIndexBenchCount(
        state.mirrorIndex,
        bench.id,
        state.mirrorRecordsByBench,
    );
    const previewCount = assetIndexBenchCount(
        state.previewIndex,
        bench.id,
        state.previewRecordsByBench,
    );
    bench.indexMirrorCount = mirrorCount;
    bench.indexPreviewCount = previewCount;
    if (mirrorCount || previewCount) {
        bench.mirrorStatus = "ready";
    }
    if (plan) {
        bench.mirrorStatus = firstString(bench.mirrorStatus, plan?.mirror_status);
        bench.mirrorNotice = firstString(bench.mirrorNotice, plan?.license?.notice);
        bench.license = firstString(bench.license, plan?.license?.label);
    }
}

function mirrorStatusLabel(value) {
    const status = String(value || "").toLocaleLowerCase();
    if (!status) {
        return "";
    }
    if (status === "ready") {
        return "站内镜像已就绪";
    }
    if (status === "allowed" || status.includes("already_full")) {
        return "可镜像 / 元数据已完整";
    }
    if (status.includes("allowed_")) {
        return "按许可边界镜像";
    }
    if (status.includes("review")) {
        return "等待许可复核";
    }
    if (status.includes("gated") || status.includes("link_only") || status.includes("prohibited")) {
        return "仅保留官方入口";
    }
    if (status.includes("metadata")) {
        return "当前仅镜像元数据";
    }
    return status.replaceAll("_", " ");
}

function inferCoverageCause(bench) {
    const audit = bench.coverageAudit || {};
    const scope = bench.catalogScope || {};
    const explicitCause = firstString(
        audit.cause,
        audit.cause_code,
        audit.reason_code,
        audit.category,
        scope.cause,
    ).toLocaleLowerCase();
    const mode = firstString(scope.mode, audit.mode, bench.coverage?.mode).toLocaleLowerCase();
    const accessClass = firstString(audit.access_class).toLocaleLowerCase();
    const combined = `${explicitCause} ${mode} ${accessClass}`;
    const publicCount = firstNumber(scope.official_public_count);
    const totalCount = firstNumber(scope.official_total_count);
    const hasPrivateBoundary = publicCount > 0
        && totalCount > publicCount
        && /private|代表公开|lite|gated|subset/.test(combined);

    if (/unit|dimension|module|page_browser|battle|floating/.test(mode)) {
        return "unit_mismatch";
    }
    if (hasPrivateBoundary) {
        return "public_limited";
    }
    if (/full|complete|all_public|all-published/.test(combined)
        && !/subset|gated|private|protocol|dimension|module|page|battle/.test(combined)) {
        return "full_catalog";
    }
    if (/sample|representative|dashboard_sampling|partial_public/.test(combined)) {
        return "dashboard_sampling";
    }
    if (/unit|dimension|module|protocol|experiment_mode|page_browser|battle|floating|example_only/.test(combined)) {
        return "unit_mismatch";
    }
    if (/gated|private|public_limited|public_subset|lite|link_only|withheld|proprietary/.test(combined)) {
        return "public_limited";
    }

    if (explicitCause || mode) {
        return audit.can_expand ? "dashboard_sampling" : "public_limited";
    }

    const isLegacyCatalog = state.catalogUrl.includes("pdf_sample_dashboard/competitor_benches.json");
    if (isLegacyCatalog && audit.can_expand && String(audit.access_class || "").includes("公开")) {
        return "dashboard_sampling";
    }
    return "public_limited";
}

function inferInfluenceTier(raw) {
    const influence = firstString(raw?.influence).toLocaleLowerCase();
    if (influence.includes("watchlist")) {
        return 1;
    }
    if (influence.includes("机构") || influence.includes("榜单")) {
        return 2;
    }
    if (influence.includes("学术")) {
        return 3;
    }
    return 4;
}

function inferRelevance(raw) {
    if (raw?.tier === "core") {
        return "直接竞品";
    }
    if (raw?.tier === "upstream") {
        return "上游能力";
    }
    return "相邻产物";
}

function resolveCandidateUrl(candidate, sourceUrl) {
    if (!candidate) {
        return "";
    }
    if (/^(?:[a-z]+:)?\/\//i.test(candidate) || candidate.startsWith("/") || candidate.startsWith("data/")) {
        return candidate;
    }
    try {
        return new URL(candidate, new URL(sourceUrl, document.baseURI)).href;
    }
    catch (_error) {
        return candidate;
    }
}

function resolvePreviewAssetUrl(candidate) {
    if (typeof candidate !== "string" || !candidate.trim()) {
        return "";
    }
    if (/^(?:[a-z]+:)?\/\//i.test(candidate) || candidate.startsWith("/")) {
        return candidate;
    }
    const baseUrl = state.activeBench?.assetBaseUrl || state.catalogUrl || document.baseURI;
    const usesLegacyAssets = String(baseUrl).includes("pdf_sample_dashboard/competitor_benches.json")
        && !candidate.startsWith("data/")
        && !candidate.startsWith("assets/");
    try {
        if (usesLegacyAssets || candidate.startsWith("./") || candidate.startsWith("../")) {
            return new URL(candidate, new URL(baseUrl, document.baseURI)).href;
        }
        return new URL(candidate, document.baseURI).href;
    }
    catch (_error) {
        return candidate;
    }
}

function isLocalUrl(value) {
    if (typeof value !== "string" || !value.trim()) {
        return false;
    }
    if (/^(?:data|blob|javascript):/i.test(value)) {
        return false;
    }
    try {
        const url = new URL(value, document.baseURI);
        return LOCAL_URL_PROTOCOLS.has(url.protocol) && url.origin === location.origin;
    }
    catch (_error) {
        return false;
    }
}

function safeHttpUrl(value) {
    if (typeof value !== "string" || !value.trim()) {
        return "";
    }
    try {
        const url = new URL(value, document.baseURI);
        return LOCAL_URL_PROTOCOLS.has(url.protocol) ? url.href : "";
    }
    catch (_error) {
        return "";
    }
}

function createExternalLink(label, url, className = "") {
    const link = createElement("a", className, label);
    link.href = safeHttpUrl(url);
    link.target = "_blank";
    link.rel = "noreferrer noopener";
    return link;
}

function createElement(tagName, className = "", text = "") {
    const element = document.createElement(tagName);
    if (className) {
        element.className = className;
    }
    if (text !== "" && text !== null && text !== undefined) {
        element.textContent = String(text);
    }
    return element;
}

function replaceSelectOptions(select, firstLabel, options) {
    const fragment = document.createDocumentFragment();
    const first = document.createElement("option");
    first.value = "";
    first.textContent = firstLabel;
    fragment.append(first);
    options.forEach(([value, label]) => {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = label;
        fragment.append(option);
    });
    select.replaceChildren(fragment);
}

function debounce(callback, delay) {
    let timeout = null;
    return (...args) => {
        window.clearTimeout(timeout);
        timeout = window.setTimeout(() => callback(...args), delay);
    };
}

function isTypingTarget(target) {
    return target instanceof HTMLInputElement
        || target instanceof HTMLTextAreaElement
        || target instanceof HTMLSelectElement
        || target?.isContentEditable;
}

function asArray(value) {
    if (Array.isArray(value)) {
        return value;
    }
    if (value === undefined || value === null || value === "") {
        return [];
    }
    if (typeof value === "object") {
        return Object.values(value);
    }
    return [value];
}

function uniqueStrings(values) {
    return [...new Set(values.map((value) => String(value || "").trim()).filter(Boolean))];
}

function firstString(...values) {
    const value = values.find((item) => typeof item === "string" && item.trim());
    return value ? value.trim() : "";
}

function firstNumber(...values) {
    for (const value of values) {
        const number = Number(value);
        if (Number.isFinite(number)) {
            return number;
        }
    }
    return 0;
}

function clampNumber(value, minimum, maximum) {
    return Math.min(maximum, Math.max(minimum, value));
}

function formatNumber(value) {
    return new Intl.NumberFormat("zh-CN").format(Number(value) || 0);
}

function formatBytes(value) {
    const bytes = Number(value) || 0;
    if (bytes < 1024) {
        return `${bytes} B`;
    }
    if (bytes < 1024 * 1024) {
        return `${(bytes / 1024).toFixed(1)} KB`;
    }
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function deliverableLabel(value) {
    return DELIVERABLE_LABELS.get(value) || value;
}

function fileExtension(value) {
    const clean = String(value || "").split(/[?#]/)[0];
    const match = clean.match(/\.([a-z0-9]+)$/i);
    return match ? match[1].toLocaleLowerCase() : "";
}

function looksLikeUrl(value) {
    return /^(?:\.?\.?\/|\/|https?:\/\/)/i.test(String(value || ""));
}

function localeSort(a, b) {
    return String(a).localeCompare(String(b), "zh-CN");
}
