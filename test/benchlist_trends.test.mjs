import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
import test from "node:test";
import vm from "node:vm";

const SOURCE = await readFile(new URL("../site/benchlist.js", import.meta.url), "utf8");
const SCOPE = {startDate: "2026-03-14", endDate: "2026-09-14", months: 6, asOf: "2026-09-14"};

function helpers(data, document = {baseURI: "https://example.test/bench-monitor/"}) {
    const sandbox = {document, URL, __data: data};
    vm.createContext(sandbox);
    const marker = "    globalThis.KwBenchList = {";
    assert.ok(SOURCE.includes(marker), "BenchList closure export marker changed");
    assert.ok(SOURCE.includes("    function buildTrendData("), "Production bundle must include the trend calculation");
    vm.runInContext(SOURCE.replace(marker, "    state.data = globalThis.__data;\n"
        + "    globalThis.__trends = {coverageSummary, buildTrendData, withAuditCache, uniqueConfirmed, trendSvg, renderTrendDetail};\n" + marker), sandbox);
    return sandbox.__trends;
}

function release(model, date, extra = {}) {
    return {model, countingModel: model, provider: "Example", releaseDate: date, eligible: true,
        dateSources: [{url: "https://example.test/official-release", title: "Official release", location: "Date"}],
        ...extra};
}

function claim(model, extra = {}) {
    return {model, countingModel: model, releaseDate: "2026-06-01", inScope: true, status: "confirmed",
        kind: "release_main", sourceUrl: "https://example.test/model-release", ...extra};
}

function dataFor(modelRegistry, benchmarks = [], modelScope = SCOPE) {
    return {modelRegistry, benchmarks, modelScope};
}

// Only the DOM operations needed by the real SVG/detail renderers; no layout or browser behavior is simulated.
class TestElement {
    constructor(tag) {
        this.tagName = tag.toUpperCase();
        this.children = [];
        this.attributes = new Map();
        this.listeners = new Map();
        this.className = "";
        this.dataset = {};
        this.hidden = false;
        this.ownText = "";
    }

    append(...nodes) {
        this.children.push(...nodes);
    }

    replaceChildren(...nodes) {
        this.ownText = "";
        this.children = nodes;
    }

    setAttribute(name, value) {
        this.attributes.set(name, String(value));
    }

    getAttribute(name) {
        return this.attributes.get(name) ?? null;
    }

    addEventListener(name, callback) {
        this.listeners.set(name, callback);
    }

    set textContent(value) {
        this.ownText = String(value);
        this.children = [];
    }

    get textContent() {
        return this.ownText + this.children.map((child) => typeof child === "string" ? child : child.textContent).join("");
    }

    querySelectorAll(tag) {
        return this.children.flatMap((child) => typeof child === "string" ? []
            : [...(child.tagName.toLowerCase() === tag ? [child] : []), ...child.querySelectorAll(tag)]);
    }

    querySelector(tag) {
        return this.querySelectorAll(tag)[0] || null;
    }
}

function testDocument() {
    return {baseURI: "https://example.test/bench-monitor/", createElement: (tag) => new TestElement(tag),
        createElementNS: (_namespace, tag) => new TestElement(tag)};
}

test("coverage denominator includes uncited eligible models and merges variants across the entire window", () => {
    const row = {id: "coverage", claimReviews: [claim("Sol"), claim("Terra"), claim("GPT-6"),
        claim("Old"), claim("Unknown date")], additionalCitations: [claim("Sol", {kind: "release_appendix"})]};
    const data = dataFor([
        release("Sol", "2026-04-01", {countingModel: "GPT-5.6"}),
        release("Terra", "2026-06-01", {countingModel: "GPT-5.6"}), release("GPT-6", "2026-08-01"),
        release("Uncited", "2026-05-01"), release("Old", "2026-03-13"), release("Unknown date", null),
    ], [row]);
    const api = helpers(data);
    const summary = api.coverageSummary(row);
    assert.equal(summary.count, 2);
    assert.equal(summary.total, 3);
    assert.ok(Math.abs(summary.percent - 200 / 3) < 1e-10);
    assert.equal(api.coverageSummary({claimReviews: []}).percent, 0);
    assert.equal(api.buildTrendData([row]).rows[0].total, summary.count);
});

test("calendar bins retain partial March and September and clip their inclusive boundaries", () => {
    const data = dataFor([release("First", "2026-03-14"), release("Last", "2026-09-14")]);
    const result = helpers(data).buildTrendData([]);
    assert.deepEqual(Array.from(result.periods, (period) => period.key),
        ["2026-03", "2026-04", "2026-05", "2026-06", "2026-07", "2026-08", "2026-09"]);
    assert.equal(result.periods[0].startDate, "2026-03-14");
    assert.equal(result.periods[0].endDate, "2026-03-31");
    assert.equal(result.periods[6].startDate, "2026-09-01");
    assert.equal(result.periods[6].endDate, "2026-09-14");
    assert.deepEqual(Array.from(result.periods, (period) => period.partial), [true, false, false, false, false, false, true]);
    assert.equal(result.periods[0].total, 1);
    assert.equal(result.periods[6].total, 1);
});

test("each variant stays in its actual release month, each month deduplicates it, and all original evidence survives", () => {
    const first = claim("Sol");
    const appendix = claim("Sol", {kind: "release_appendix"});
    const later = claim("Luna");
    const row = {id: "variant", claimReviews: [first, appendix, later, claim("Terra")],
        additionalCitations: [claim("Sol", {kind: "comparison_only"}), claim("Luna", {kind: "third_party"})]};
    const data = dataFor([
        release("Sol", "2026-04-01", {countingModel: "GPT-5.6"}),
        release("Luna", "2026-06-01", {countingModel: "GPT-5.6"}),
        release("Terra", "2026-06-20", {countingModel: "GPT-5.6"}),
    ], [row]);
    const result = helpers(data).buildTrendData([row]);
    assert.equal(result.rows[0].points[1].count, 1);
    assert.equal(result.rows[0].points[3].count, 1);
    assert.equal(result.periods[3].total, 1);
    assert.equal(result.rows[0].points[1].claims[0], first);
    assert.equal(result.rows[0].points[1].claims[1], appendix);
    assert.equal(result.rows[0].points[3].claims[0], later);
    assert.equal(result.rows[0].points[3].claims.length, 2);
    assert.equal(result.rows[0].total, 1);
    assert.equal(result.rows[0].points.reduce((sum, point) => sum + point.count, 0), 2);
    assert.equal(result.maxCount, 1);
});

test("same-month date ranges can be binned while uncertain cross-month releases only contribute to whole-window coverage", () => {
    const row = {id: "ranges", claimReviews: [claim("April"), claim("Cross-month"), claim("Unknown"), claim("Outside range")]};
    const data = dataFor([
        release("April", null, {releaseDateRange: {start: "2026-04-01", end: "2026-04-30"}}),
        release("Cross-month", null, {releaseDateRange: {start: "2026-05-25", end: "2026-06-05"}}),
        release("Unknown", null),
        release("Outside range", null, {releaseDateRange: {start: "2026-03-01", end: "2026-03-31"}}),
    ], [row]);
    const api = helpers(data);
    const result = api.buildTrendData([row, {...row, id: "same-evidence-another-benchmark"}]);
    assert.equal(result.excludedTimingCount, 1, "timing exclusions count releases, not repeated benchmark evidence");
    assert.equal(result.periods.reduce((sum, period) => sum + period.total, 0), 1);
    assert.equal(result.rows[0].points[1].count, 1);
    assert.equal(result.rows[0].total, 2);
    assert.equal(api.coverageSummary(row).total, 2);
    assert.equal(api.coverageSummary(row).percent, 100);
    assert.equal(result.rows[0].points[2].percent, null);
    assert.equal(result.rows[0].points[3].percent, null);
});

test("trend change compares coverage in first and last complete months, not raw model growth or partial months", () => {
    const models = [release("March", "2026-03-20"), release("April A", "2026-04-02"),
        release("April B", "2026-04-10"), ...[1, 2, 3, 4].map((n) => release(`August ${n}`, "2026-08-10")),
        release("September", "2026-09-01")];
    const row = {id: "normalized", claimReviews: [claim("March"), claim("April A"), claim("August 1"), claim("August 2")]};
    const result = helpers(dataFor(models, [row])).buildTrendData([row]);
    assert.equal(result.rows[0].points[0].percent, 100);
    assert.equal(result.rows[0].points[6].percent, 0);
    assert.equal(result.rows[0].points[1].percent, 50);
    assert.equal(result.rows[0].points[5].percent, 50);
    assert.equal(result.rows[0].change, 0);
    assert.equal(result.rows[0].countChange, 1);
});

test("empty denominators and insufficient complete months produce unknown coverage changes", () => {
    const row = {id: "empty-early", claimReviews: [claim("August")]};
    const data = dataFor([release("August", "2026-08-10")], [row]);
    const trend = helpers(data).buildTrendData([row]).rows[0];
    assert.equal(trend.points[1].percent, null);
    assert.equal(trend.change, null);
    assert.equal(trend.countChange, 1);
    const single = dataFor(data.modelRegistry, [row], {startDate: "2026-08-01", endDate: "2026-08-31"});
    const singleTrend = helpers(single).buildTrendData([row]).rows[0];
    assert.equal(singleTrend.change, null);
    assert.equal(singleTrend.countChange, null);
    const emptyData = dataFor([], [row]);
    const api = helpers(emptyData);
    assert.equal(api.coverageSummary(row).count, 0);
    assert.equal(api.coverageSummary(row).total, 0);
    assert.equal(api.coverageSummary(row).percent, null);
});

test("uncertain, third-party, corrected and unsafe-source claims do not enter monthly numerators", () => {
    const models = ["Unverified", "Comparison", "ThirdParty", "Corrected", "Unsafe", "Valid"].map((name) =>
        release(name, "2026-05-01"));
    const row = {id: "statuses", claimReviews: [claim("Unverified", {status: "unverified"}),
        claim("Comparison", {kind: "comparison_only"}), claim("ThirdParty", {kind: "third_party"}),
        claim("Corrected", {status: "corrected"}), claim("Unsafe", {sourceUrl: "javascript:alert(1)"}), claim("Valid")]};
    const result = helpers(dataFor(models, [row])).buildTrendData([row]);
    assert.equal(result.periods[2].total, 6);
    assert.equal(result.rows[0].points[2].count, 1);
    assert.deepEqual(Array.from(result.rows[0].points[2].models), ["Valid"]);
    assert.equal(result.rows[0].points[2].claims.length, 1);
});

test("calendar handling supports year boundaries, leap days and malformed scope without invented bins", () => {
    const leap = dataFor([], [], {startDate: "2023-12-15", endDate: "2024-03-10"});
    const periods = helpers(leap).buildTrendData([]).periods;
    assert.deepEqual(Array.from(periods, (period) => period.key), ["2023-12", "2024-01", "2024-02", "2024-03"]);
    assert.equal(periods[2].endDate, "2024-02-29");
    const invalid = dataFor([], [], {startDate: "2026-04-31", endDate: "2026-09-14"});
    assert.equal(helpers(invalid).buildTrendData([]).periods.length, 0);
});

test("large and small trend SVGs render both metrics, preserve zeroes and break lines across absent cohorts", () => {
    const api = helpers(dataFor([]), testDocument());
    const periods = ["2026-03", "2026-04", "2026-05", "2026-06", "2026-07"].map((key, index) =>
        ({key, partial: index === 0 || index === 4}));
    const series = {points: [
        {count: 1, total: 2, percent: 50}, {count: 2, total: 2, percent: 100},
        {count: 0, total: 0, percent: null}, {count: 0, total: 2, percent: 0},
        {count: 1, total: 2, percent: 50},
    ]};
    for (const metric of ["count", "coverage"]) {
        for (const large of [false, true]) {
            const svg = api.trendSvg(series, periods, metric, metric === "coverage" ? 100 : 2, large);
            const lines = svg.querySelectorAll("line").filter((node) => node.getAttribute("stroke") === "currentColor");
            assert.equal(lines.length, 2, "no line may connect across the month without any released models");
            assert.ok(lines.every((line) => line.getAttribute("stroke-dasharray") === "4 3"));
            const circles = svg.querySelectorAll("circle");
            assert.equal(circles.length, 4, "zero references remains a visible point; absent cohorts do not");
            assert.equal(circles[0].getAttribute("fill"), "white");
            assert.equal(circles[3].getAttribute("fill"), "white");
            assert.match(svg.getAttribute("aria-label"), /2026-05：无发布模型/);
            assert.ok(circles.every((node) => Number.isFinite(Number(node.getAttribute("cy")))));
            if (large) {
                const labels = svg.querySelectorAll("text").map((node) => node.textContent);
                assert.ok(labels.includes("3月*"));
                assert.ok(labels.includes("7月*"));
                assert.ok(labels.includes("5月"));
            }
        }
    }
});

test("missing release scope and an empty audit produce safe detail states instead of rendering undefined points", () => {
    const row = {id: "missing-scope", name: "Example", category: "Coding", claimReviews: []};
    const data = {benchmarks: [row], modelRegistry: []};
    const api = helpers(data, testDocument());
    const view = {selected: row.id, period: null, metric: "count", data: api.buildTrendData([row]),
        detail: new TestElement("section"), scroll: new TestElement("div")};
    assert.doesNotThrow(() => api.renderTrendDetail(view));
    assert.match(view.detail.textContent, /窗口.*未配置/);
    const emptyApi = helpers(dataFor([]), testDocument());
    const emptyView = {selected: null, data: emptyApi.buildTrendData([]), detail: new TestElement("section")};
    assert.doesNotThrow(() => emptyApi.renderTrendDetail(emptyView));
    assert.equal(emptyView.detail.hidden, true);
    assert.equal(emptyView.detail.children.length, 0);
});

test("the real HLE August drilldown renders its full SVG and actual source links", async () => {
    const data = JSON.parse(await readFile(new URL("../site/benchlist.json", import.meta.url), "utf8"));
    const api = helpers(data, testDocument());
    const row = data.benchmarks.find((item) => item.name === "HLE");
    const trends = api.buildTrendData(data.benchmarks);
    const august = trends.periods.findIndex((period) => period.key === "2026-08");
    const view = {selected: row.id, period: august, metric: "coverage", data: trends,
        detail: new TestElement("section"), scroll: new TestElement("div")};
    assert.doesNotThrow(() => api.renderTrendDetail(view));
    assert.equal(view.detail.hidden, false);
    assert.match(view.detail.textContent, /7 \/ 16 个模型/);
    assert.equal(view.detail.querySelectorAll("svg").length, 1);
    assert.ok(view.detail.querySelectorAll("a").length >= 7);
});

test("real audit trends preserve global totals and finish within the interaction budget", async () => {
    const data = JSON.parse(await readFile(new URL("../site/benchlist.json", import.meta.url), "utf8"));
    const api = helpers(data);
    const start = performance.now();
    const result = api.buildTrendData(data.benchmarks);
    const elapsed = performance.now() - start;
    assert.equal(result.rows.length, data.benchmarks.length);
    assert.deepEqual(Array.from(result.periods, (period) => period.total), [7, 25, 7, 14, 11, 16, 9]);
    assert.equal(api.coverageSummary(data.benchmarks[0]).total, 88);
    const hle = data.benchmarks.find((row) => row.name === "HLE");
    assert.ok(hle, "HLE audit row exists");
    const hleTrend = result.rows.find((row) => row.id === hle.id);
    assert.equal(hleTrend.total, 39);
    assert.deepEqual(Array.from(hleTrend.points, (point) => point.count), [4, 15, 2, 5, 4, 7, 2]);
    assert.equal(hleTrend.countChange, -8);
    assert.equal(hleTrend.change, -16.25);
    api.withAuditCache(data, () => {
        result.rows.forEach((row, index) => {
            assert.equal(row.total, api.uniqueConfirmed(data.benchmarks[index], data).length);
            row.points.forEach((point, periodIndex) => {
                assert.equal(point.total, result.periods[periodIndex].total);
                assert.ok(point.count <= point.total);
                assert.ok(point.percent === null || point.percent >= 0 && point.percent <= 100);
            });
        });
    });
    assert.ok(elapsed < 3000, `trend calculation exceeded 3 seconds: ${elapsed} ms`);
});
