import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
import test from "node:test";
import vm from "node:vm";

const SCRIPT = new URL("../site/benchlist.js", import.meta.url);
const APP = new URL("../site/app.js", import.meta.url);
const SCOPE = {asOf: "2026-09-14", startDate: "2026-03-14", endDate: "2026-09-14", months: 6};

async function contracts(config = {}) {
    let fetchCount = 0;
    const {data = {modelScope: SCOPE, benchmarks: []}, ...environment} = config;
    const sandbox = {
        document: {baseURI: "http://example.test/bench-monitor/"},
        URL,
        fetch: () => {
            fetchCount += 1;
            throw new Error("Unexpected fetch");
        },
        __benchListFixture: data,
        ...environment,
    };
    vm.createContext(sandbox);
    const source = await readFile(SCRIPT, "utf8");
    // Inject normalized fixture state without changing the shipped API or triggering activation/fetch.
    vm.runInContext(source.replace("    globalThis.KwBenchList = {",
        "    state.data = normalizeData(globalThis.__benchListFixture);\n    globalThis.KwBenchList = {"), sandbox);
    return {api: sandbox.KwBenchList.testContracts, fetchCount, sandbox};
}

const own = (model, overrides = {}) => ({
    model, countingModel: model, releaseDate: "2026-06-01", inScope: true,
    status: "confirmed", kind: "release_main", sourceUrl: "https://openai.com/release", ...overrides,
});

const release = (model, overrides = {}) => ({
    model, countingModel: model, provider: "OpenAI", releaseDate: "2026-06-01", eligible: true,
    dateSources: [{url: "https://openai.com/release", title: "Official release", location: "Publication date"}],
    ...overrides,
});

test("loading the module does not fetch audit data", async () => {
    const {fetchCount} = await contracts();
    assert.equal(fetchCount, 0);
});

test("same release across main text and appendix counts once; different releases count separately", async () => {
    const {api} = await contracts();
    const row = {
        claimReviews: [own("GPT-5.4"), own("gpt 5.4", {kind: "release_appendix"})],
        additionalCitations: [own("GPT-5.4"), own("GPT-5.3")],
    };
    assert.equal(api.uniqueConfirmed(row).length, 2);
    assert.equal(api.cellSummary(row, "OpenAI").confirmed.length, 2);
});

test("third party, comparison-only, corrected, unverified and missing-source claims never raise own-release counts", async () => {
    const {api} = await contracts();
    const row = {claimReviews: [
        own("GPT-5.4", {kind: "comparison_only"}),
        own("GPT-5.3", {kind: "third_party"}),
        own("GPT-5.2", {status: "corrected"}),
        own("GPT-5.1", {status: "unverified"}),
        own("GPT-5", {sourceUrl: ""}),
        own("GPT-4.1", {sourceUrl: "javascript:alert(1)"}),
    ]};
    assert.equal(api.uniqueConfirmed(row).length, 0);
    assert.equal(api.cellSummary(row, "OpenAI").unresolved.length, 6);
});

test("an original with a verified in-window release date can remain unresolved without a citation", async () => {
    const model = "Claude Opus 5";
    const {api} = await contracts({data: {modelScope: SCOPE, benchmarks: [],
        modelRegistry: [release(model, {provider: "Anthropic"})]}});
    const row = {originalModels: [model, model], originalClaimModels: [model], claimReviews: []};
    const cell = api.cellSummary(row, "Anthropic");
    assert.equal(cell.originals.length, 1);
    assert.equal(cell.unresolved.length, 1);
    assert.equal(cell.confirmed.length, 0);
});

test("raw original models without verified release scope remain readable but never count", async () => {
    const {api} = await contracts();
    const row = {originalModels: ["Unknown release"], claimReviews: []};
    assert.equal(api.originals(row)[0], "Unknown release");
    assert.equal(api.rowOriginals(row).length, 0);
    assert.equal(api.columnsFor([row], "model").length, 0);
});

test("GPT-5.6 Sol Terra Luna merge across citations and original claims while GPT-6 stays independent", async () => {
    const variants = ["GPT-5.6 Sol", "GPT-5.6 Terra", "GPT-5.6 Luna"];
    const modelRegistry = [...variants.map((model) => release(model, {countingModel: "GPT-5.6"})), release("GPT-6")];
    const {api} = await contracts({data: {modelScope: SCOPE, modelRegistry, benchmarks: []}});
    const row = {originalModels: variants, originalClaimModels: ["GPT-5.6", "GPT-6"],
        claimReviews: [...variants.map((model) => own(model, {countingModel: "GPT-5.6"})), own("GPT-6")],
        additionalCitations: [own("GPT-5.6 Luna", {countingModel: "GPT-5.6", kind: "release_appendix"})]};
    assert.equal(api.uniqueConfirmed(row).length, 2);
    assert.equal(api.cellSummary(row, "OpenAI").confirmed.length, 2);
    assert.equal(api.cellSummary(row, api.releaseKey("GPT-5.6"), "model").confirmed.length, 1);
    assert.equal(api.cellSummary(row, api.releaseKey("GPT-6"), "model").confirmed.length, 1);
    assert.equal(api.rowOriginals(row).length, 2);
    assert.equal(api.cellSummary(row, "OpenAI").unresolved.length, 0);
    assert.equal(api.columnsFor([row], "model").length, 2);
    assert.equal(api.registrySummary().included.length, 4);
    assert.equal(api.registrySummary().countingModels.length, 2);
    assert.equal(api.reviews(row).length, 5);
    assert.equal(api.reviews(row)[0].model, "GPT-5.6 Sol");
});

test("only the inclusive six-month date window counts, even if a stale claim says inScope", async () => {
    const dates = ["2026-03-13", "2026-03-14", "2026-09-14", "2026-09-15", null, "2026-02-30"];
    const row = {claimReviews: dates.map((releaseDate, index) => own(`Model ${index}`, {releaseDate}))};
    const {api} = await contracts();
    assert.equal(api.uniqueConfirmed(row).length, 2);
    assert.equal(api.rowOriginals(row).length, 2);
    assert.equal(api.columnsFor([row], "model").length, 2);
    assert.equal(api.reviews(row).length, 6);
    assert.match(api.claimScope(row.claimReviews[0]).reason, /窗口外/);
    assert.match(api.claimScope(row.claimReviews[4]).reason, /日期未核实/);
});

test("registry exclusions and unverified claim scope fail closed and preserve readable evidence", async () => {
    const modelRegistry = [release("Old model", {eligible: false, exclusionReason: "版本日期仍待核验"}),
        release("Known model"), release("No date", {releaseDate: null, eligible: true})];
    const {api} = await contracts({data: {modelScope: SCOPE, modelRegistry, benchmarks: []}});
    const row = {originalClaimModels: ["Old model", "Known model", "No date"],
        claimReviews: [own("Old model"), own("Known model", {inScope: false}),
        own("No date"), own("Unregistered model")]};
    assert.equal(api.uniqueConfirmed(row).length, 0);
    assert.equal(api.rowOriginals(row).length, 0);
    assert.equal(api.reviews(row).length, 4);
    assert.equal(api.claimScope(row.claimReviews[0]).reason, "版本日期仍待核验");
    assert.match(api.claimScope(row.claimReviews[3]).reason, /发布清单尚无/);
    assert.equal(api.registrySummary().excluded.length, 2);
});

test("an officially sourced release month fully inside the window counts without inventing a day", async () => {
    const modelRegistry = [release("April release", {releaseDate: null,
        releaseDateRange: {start: "2026-04-01", end: "2026-04-30"}})];
    const {api} = await contracts({data: {modelScope: SCOPE, modelRegistry, benchmarks: []}});
    const row = {claimReviews: [own("April release", {releaseDate: null})]};
    assert.equal(api.uniqueConfirmed(row).length, 1);
    assert.equal(api.columnsFor([], "model").length, 1);
    assert.equal(api.rowOriginals(row).length, 1);
    const info = api.claimScope(row.claimReviews[0]);
    assert.equal(info.releaseDate, null);
    assert.equal(info.releaseDateRange.start, "2026-04-01");
    assert.equal(api.releaseDateLabel(info), "2026-04（月内，具体日期未公布）");
});

test("partial-window, invalid, unsourced and explicitly excluded date ranges never count", async () => {
    const ranges = [
        {start: "2026-03-01", end: "2026-03-31"},
        {start: "2026-09-01", end: "2026-09-30"},
        {start: "2026-04-30", end: "2026-04-01"},
        {start: "2026-04-01", end: "2026-04-31"},
    ];
    const modelRegistry = ranges.map((releaseDateRange, index) => release(`Range ${index}`,
        {releaseDate: null, releaseDateRange}));
    const april = {releaseDate: null, releaseDateRange: {start: "2026-04-01", end: "2026-04-30"}};
    modelRegistry.push(release("No source", {...april, dateSources: []}),
        release("Unsafe source", {...april, dateSources: [{url: "javascript:alert(1)"}]}),
        release("Excluded range", {...april, eligible: false}));
    const {api} = await contracts({data: {modelScope: SCOPE, modelRegistry, benchmarks: []}});
    const row = {claimReviews: modelRegistry.map((item) => own(item.model))};
    assert.equal(api.uniqueConfirmed(row).length, 0);
    assert.equal(api.registrySummary().included.length, 0);
    assert.equal(api.reviews(row).length, 7);
    assert.match(api.releaseScope(modelRegistry[0]).reason, /未完整落在/);
    assert.match(api.releaseScope(modelRegistry[4]).reason, /缺少.*来源/);
    assert.equal(api.releaseDateLabel(modelRegistry[2]), "未核实");
});

test("range boundaries stay inclusive and a partial month is displayed as its actual range", async () => {
    const {api} = await contracts();
    const item = release("Bounded release", {releaseDate: null,
        releaseDateRange: {start: SCOPE.startDate, end: SCOPE.endDate}});
    assert.equal(api.releaseScope(item).eligible, true);
    assert.equal(api.releaseDateLabel(item), "2026-03-14 — 2026-09-14（日期范围）");
    assert.equal(api.releaseDateLabel(release("Exact date")), "2026-06-01");
});

test("render caching preserves model and provider cells, variant deduplication and unresolved originals", async () => {
    const data = {modelScope: SCOPE, modelRegistry: [
        release("GPT-5.6 Sol", {countingModel: "GPT-5.6"}),
        release("GPT-5.6 Luna", {countingModel: "GPT-5.6"}), release("GPT-6"),
        release("April model", {provider: "Example", releaseDate: null,
            releaseDateRange: {start: "2026-04-01", end: "2026-04-30"}}),
        release("Old model", {releaseDate: "2026-02-01"}),
    ], benchmarks: [
        {claimReviews: [own("GPT-5.6 Sol"), own("GPT-5.6 Luna"),
            own("GPT-6", {status: "ambiguous"}), own("Old model")],
            additionalCitations: [own("GPT-5.6 Luna", {kind: "release_appendix"})]},
        {claimReviews: [own("April model"), own("GPT-6", {kind: "comparison_only"})]},
        {originalClaimModels: ["GPT-6"], claimReviews: []},
    ]};
    const {api} = await contracts({data});
    const snapshot = () => JSON.stringify(["model", "provider"].map((projection) => {
        const columns = api.columnsFor(data.benchmarks, projection, data);
        return {columns, rows: data.benchmarks.map((row) => ({
            confirmed: api.uniqueConfirmed(row, data), originals: api.rowOriginals(row, data),
            cells: columns.map(([key]) => api.cellSummary(row, key, projection, data)),
        }))};
    }));
    const expected = snapshot();
    assert.equal(api.withAuditCache(data, snapshot), expected);
    assert.equal(api.withAuditCache(data, () => api.withAuditCache(data, snapshot)), expected);
});

test("completed and interrupted render caches do not retain changed evidence or release eligibility", async () => {
    const claim = own("GPT-6");
    const row = {claimReviews: [claim]};
    const data = {modelScope: SCOPE, modelRegistry: [release("GPT-6")], benchmarks: [row]};
    const {api} = await contracts({data});
    const count = () => api.uniqueConfirmed(row, data).length;
    assert.equal(api.withAuditCache(data, count), 1);
    claim.status = "ambiguous";
    assert.equal(api.withAuditCache(data, count), 0);
    claim.status = "confirmed";
    assert.throws(() => api.withAuditCache(data, () => {
        assert.equal(count(), 1);
        throw new Error("interrupted render");
    }), /interrupted render/);
    data.modelRegistry[0].eligible = false;
    assert.equal(count(), 0);
    assert.equal(api.withAuditCache(data, count), 0);
});

test("the shipped audit matrix computes both passes within the three-second interaction budget", async () => {
    const data = JSON.parse(await readFile(new URL("../site/benchlist.json", import.meta.url), "utf8"));
    const {api} = await contracts({data});
    const started = performance.now();
    const result = api.withAuditCache(data, () => {
        const columns = api.columnsFor(data.benchmarks, "model", data);
        let sum = 0;
        // Rendering visits every cell once for color scaling and again when creating its DOM node.
        for (let pass = 0; pass < 2; pass += 1) {
            for (const row of data.benchmarks) {
                for (const [column] of columns) {
                    sum += api.cellSummary(row, column, "model", data).confirmed.length;
                }
            }
        }
        return {sum, expected: data.benchmarks.reduce((total, row) =>
            total + api.uniqueConfirmed(row, data).length, 0) * 2};
    });
    assert.equal(result.sum, result.expected);
    assert.ok(performance.now() - started < 3000, "matrix derivation exceeded the browser interaction budget");
});

test("model pagination exposes every benchmark exactly once and leaves provider rows complete", async () => {
    const {api} = await contracts();
    const rows = Array.from({length: 127}, (_, index) => ({id: `row-${index}`}));
    const filters = {projection: "model", category: "all", query: "", priority: "all", mode: "verified"};
    let page = api.matrixPage(rows, filters);
    assert.equal(page.rows.length, 40);
    assert.equal(page.start, 1);
    assert.equal(page.end, 40);
    assert.equal(page.total, 127);
    assert.equal(page.pageCount, 4);
    const visited = [];
    for (let index = 0; index < page.pageCount; index += 1) {
        page = api.matrixPage(rows, filters, {...page, page: index});
        visited.push(...page.rows.map((row) => row.id));
    }
    assert.deepEqual(visited, rows.map((row) => row.id));
    assert.equal(page.start, 121);
    assert.equal(page.end, 127);
    assert.equal(page.rows.length, 7);
    const providers = api.matrixPage(rows, {...filters, projection: "provider"}, page);
    assert.equal(providers.rows.length, 127);
    assert.equal(providers.enabled, false);
    assert.equal(providers.page, 0);
});

test("search, category, priority and other matrix filter changes reset model pagination", async () => {
    const {api} = await contracts();
    const rows = Array.from({length: 100}, (_, id) => ({id}));
    const filters = {projection: "model", category: "all", query: "", priority: "all", mode: "verified",
        selectedOnly: false, additionsOnly: false};
    const first = api.matrixPage(rows, filters);
    const second = api.matrixPage(rows, filters, {...first, page: 1});
    assert.equal(second.page, 1);
    for (const change of [{query: "GPQA"}, {category: "Coding"}, {priority: "P0"},
        {mode: "original"}, {selectedOnly: true}, {additionsOnly: true}]) {
        assert.equal(api.matrixPage(rows, {...filters, ...change}, second).page, 0);
    }
});

test("empty, exact-sized, shrinking and out-of-range model pages have safe boundaries", async () => {
    const {api} = await contracts();
    const filters = {projection: "model"};
    const rows = Array.from({length: 80}, (_, id) => ({id}));
    const initial = api.matrixPage(rows, filters);
    const last = api.matrixPage(rows, filters, {...initial, page: 999});
    assert.equal(last.page, 1);
    assert.equal(last.rows.length, 40);
    assert.equal(last.end, 80);
    assert.equal(api.matrixPage(rows, filters, {...initial, page: -5}).page, 0);
    const smaller = api.matrixPage(rows.slice(0, 12), filters, last);
    assert.equal(smaller.page, 0);
    assert.equal(smaller.start, 1);
    assert.equal(smaller.end, 12);
    const empty = api.matrixPage([], filters, last);
    assert.equal(empty.page, 0);
    assert.equal(empty.start, 0);
    assert.equal(empty.end, 0);
    assert.equal(empty.rows.length, 0);
});

test("eligible registry models with zero citations remain as model and provider columns", async () => {
    const modelRegistry = [release("GPT-5.6 Sol", {countingModel: "GPT-5.6"}),
        release("GPT-5.6 Terra", {countingModel: "GPT-5.6"}), release("GPT-6"),
        release("Gemini New", {provider: "Google"}), release("Old release", {releaseDate: "2026-03-13"})];
    const {api} = await contracts({data: {modelScope: SCOPE, modelRegistry, benchmarks: []}});
    const row = {claimReviews: [own("GPT-6")]};
    assert.equal(api.columnsFor([row], "model").length, 3);
    assert.equal(api.columnsFor([], "model").length, 3);
    assert.equal(api.columnsFor([row], "provider").length, 2);
    assert.equal(api.cellSummary(row, "Google").confirmed.length, 0);
    assert.equal(api.cellSummary(row, "Google").originals.length, 0);
});

test("model search excludes out-of-window and unverified-date records while keeping their drawer evidence", async () => {
    const {api} = await contracts();
    const row = {name: "Example benchmark", originalModels: ["Old release"], claimReviews: [
        own("GPT-5.6 Sol", {countingModel: "GPT-5.6"}),
        own("Old release", {releaseDate: "2026-01-01", note: "archived clue"}),
        own("Unknown date", {releaseDate: null, note: "uncertain clue"}),
    ]};
    assert.equal(api.matchesQuery(row, "GPT-5.6"), true);
    assert.equal(api.matchesQuery(row, "Sol"), true);
    assert.equal(api.matchesQuery(row, "Old release"), false);
    assert.equal(api.matchesQuery(row, "archived clue"), false);
    assert.equal(api.matchesQuery(row, "uncertain clue"), false);
    assert.equal(api.reviews(row).length, 3);
});

test("missing or malformed modelScope never silently falls back to all historical releases", async () => {
    const {api} = await contracts({data: {benchmarks: []}});
    const row = {claimReviews: [own("GPT-6")]};
    assert.equal(api.uniqueConfirmed(row).length, 0);
    assert.match(api.scopeLabel(), /尚未配置/);
    assert.match(api.claimScope(row.claimReviews[0]).reason, /窗口未配置/);
});

test("canonical original claim models replace grouped source labels without creating phantom model columns", async () => {
    const {api} = await contracts();
    const row = {
        originalModels: ["Claude Opus5/Fable5.1"],
        originalClaimModels: ["Claude Opus 5", "Claude Fable 5.1", "Claude Opus 5"],
        claimReviews: [own("Claude Opus 5"), own("Claude Fable 5.1")],
        additionalCitations: [own("GPT-5.4")],
    };
    assert.equal(api.rowOriginals(row).length, 2);
    assert.equal(api.originals(row)[0], "Claude Opus5/Fable5.1");
    assert.equal(api.cellSummary(row, "Anthropic").originals.length, 2);
    assert.equal(api.cellSummary(row, "Anthropic").unresolved.length, 0);
    const columns = api.columnsFor([row], "model");
    assert.equal(columns.length, 3);
    assert.equal(columns.some(([, name]) => name === "Claude Opus5/Fable5.1"), false);
});

test("expanded claimReviews are the original counting fallback when canonical list is absent", async () => {
    const {api} = await contracts();
    const row = {
        originalModels: ["GPT-5.4/5.3"],
        claimReviews: [own("GPT-5.4"), own("GPT-5.3"), own("gpt 5.4", {kind: "release_appendix"})],
    };
    assert.equal(api.rowOriginals(row).length, 2);
    assert.equal(api.columnsFor([row], "model").length, 2);
    assert.equal(api.cellSummary(row, "OpenAI").unresolved.length, 0);
});

test("an explicitly empty canonical original list stays empty", async () => {
    const {api} = await contracts();
    const row = {originalModels: ["旧的组名"], originalClaimModels: [], claimReviews: [own("GPT-5.4")]};
    assert.equal(api.rowOriginals(row).length, 0);
    assert.equal(api.uniqueConfirmed(row).length, 1);
});

test("only explicit new benchmark rows appear in additions filter; extra citations do not mark an existing benchmark", async () => {
    const {api} = await contracts();
    const rows = [
        {id: "original", additionalCitations: [own("GPT-5.4")]},
        {id: "new-benchmark", isAddition: true, additionalCitations: [own("Claude Opus 5")]},
        {id: "another-original", isAddition: false},
    ];
    assert.equal(api.filterAdditions(rows, true).length, 1);
    assert.equal(api.filterAdditions(rows, true)[0].id, "new-benchmark");
    assert.equal(api.filterAdditions(rows, false).length, 3);
});

test("model projection separates exact releases and provider projection unifies releases", async () => {
    const {api} = await contracts();
    const row = {claimReviews: [own("Gemini 3.1 Pro"), own("Gemini 3 Pro"), own("Claude Sonnet 4.6")]};
    assert.equal(api.cellSummary(row, "Google").confirmed.length, 2);
    assert.equal(api.cellSummary(row, api.releaseKey("Gemini 3.1 Pro"), "model").confirmed.length, 1);
    assert.equal(api.columnsFor([row], "provider").length, 2);
    assert.equal(api.columnsFor([row], "model").length, 3);
});

test("an evidence record for a benchmark addition does not pretend it was in the original document", async () => {
    const {api} = await contracts();
    const row = {isAddition: true, originalModels: [], additionalCitations: [own("GPT-5.4")]};
    const cell = api.cellSummary(row, "OpenAI");
    assert.equal(cell.confirmed.length, 1);
    assert.equal(cell.originals.length, 0);
});

test("source and download links reject active URLs and credentials; public view hides internal URLs", async () => {
    const {api, sandbox} = await contracts();
    assert.equal(api.safeUrl("javascript:alert(1)"), "");
    assert.equal(api.safeUrl("https://user:password@example.test/file"), "");
    assert.equal(api.safeUrl("https://external.test/screenshot.png", true), "");
    assert.equal(api.safeUrl("data/benchlist.json", true), "http://example.test/bench-monitor/data/benchlist.json");
    sandbox.KW_BENCH_PUBLIC_MODE = true;
    assert.equal(api.safeUrl("https://ku.baidu-int.com/knowledge/a"), "");
    assert.equal(api.safeUrl("http://10.25.66.233/bench-monitor/"), "");
});

test("data normalization preserves future categories and rejects duplicate row identities", async () => {
    const {api} = await contracts();
    const data = api.normalizeData({benchmarks: [{id: "x", category: "Robotics", priority: "p1"}]});
    assert.equal(data.benchmarks[0].category, "Robotics");
    assert.equal(data.benchmarks[0].priority, "P1");
    assert.throws(() => api.normalizeData({benchmarks: [{id: "x"}, {id: "x"}]}), /重复条目/);
});

function element() {
    const classes = new Set();
    return {
        style: {},
        classList: {
            add: (name) => classes.add(name),
            remove: (name) => classes.delete(name),
            contains: (name) => classes.has(name),
            toggle: (name, value) => value ? classes.add(name) : classes.delete(name),
        },
        setAttribute() {},
        querySelectorAll: () => [],
    };
}

async function routing() {
    const calls = [];
    const body = element();
    const sandbox = {
        console, URL, URLSearchParams,
        document: {body, addEventListener() {}, baseURI: "http://example.test/bench-monitor/"},
        window: {innerWidth: 1400, scrollTo() {}},
        location: {hash: "#view=benchlist", pathname: "/bench-monitor/", search: ""},
        history: {replaceState() {}},
        KwBenchList: {
            activate: () => {
                calls.push("activate");
                body.classList.add("benchlist-active");
            },
            deactivate: () => {
                calls.push("deactivate");
                body.classList.remove("benchlist-active");
            },
        },
    };
    vm.createContext(sandbox);
    const source = await readFile(APP, "utf8");
    vm.runInContext(`${source}\n;globalThis.routing = {state, dom, handleHashChange, showCatalogHome, showLoader};`, sandbox);
    const api = sandbox.routing;
    for (const key of ["catalogHome", "benchWorkspace", "ingestionWorkspace", "fatalState", "loadingLayer",
        "benchSidebar", "sidebarScrim", "mobileMenuButton", "benchGroups", "navStatusDot", "navStatusText"] ) {
        api.dom[key] = element();
    }
    return {api, calls, sandbox};
}

test("BenchList deep link activates before catalog data exists and catalog completion does not reopen it", async () => {
    const {api, calls} = await routing();
    api.state.benches = [];
    api.handleHashChange();
    assert.equal(calls.filter((call) => call === "activate").length, 1);
    assert.equal(api.dom.catalogHome.classList.contains("hidden"), true);
    assert.equal(api.dom.loadingLayer.classList.contains("hidden"), true);
    api.handleHashChange();
    assert.equal(calls.filter((call) => call === "activate").length, 1);
});

test("returning to catalog deactivates BenchList and restores the catalog workspace", async () => {
    const {api, calls, sandbox} = await routing();
    api.handleHashChange();
    sandbox.location.hash = "";
    api.state.benches = [{id: "example"}];
    api.handleHashChange();
    assert.equal(calls.at(-1), "deactivate");
    assert.equal(api.dom.catalogHome.classList.contains("hidden"), false);
});
