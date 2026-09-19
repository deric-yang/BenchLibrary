import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
import test from "node:test";
import vm from "node:vm";
async function loadApp() {
 const source=await readFile(new URL("../site/app.js", import.meta.url), "utf8");
 const sandbox={URL,console,document:{addEventListener(){},baseURI:"http://example.test/bench-monitor/"},location:{origin:"http://example.test"}};
 vm.createContext(sandbox);
 vm.runInContext(source+"\n;globalThis.api={state,normalizeMaterial,mergeIndexedMaterials,resolvePreviewSpec,scoreIndexedRecord};",sandbox);
 return {api:sandbox.api};
}
function resetIndexes(api,benchId,mirrorRecords=[],previewRecords=[]) {
 api.state.activeBenchId=benchId;
 api.state.mirrorRecordsByBench=new Map([[benchId,mirrorRecords]]);
 api.state.previewRecordsByBench=new Map([[benchId,previewRecords]]);
}

function workbookFixture(api) {
    const archive = "https://example.org/workbooks.tar.gz";
    const files = [1, 2, 3].map((n) => ({
        filename: `${n}_input.xlsx`, archive_path: `data/task-1/${n}_input.xlsx`,
        source_url: archive, url: `assets/mirrors/${n}_input.xlsx`,
        preview: {status: "conversion_required", preview_kind: "pdf", preview_url: ""},
    }));
    const mirrors = files.map((file, i) => ({
        bench_id: "bench-a", task_id: "task-1", role: "input", status: "ready",
        filename: file.filename, logical_path: file.archive_path, source_url: archive,
        view_path: file.url, sha256: `hash-${i + 1}`,
    }));
    const preview = {...mirrors[0], source_sha256: "hash-1", preview_kind: "pdf",
        preview_url: "assets/previews/first.pdf", source_view_path: mirrors[0].view_path};
    const task = {id: "task-1", raw: {source: {files}, preview: {preview_kind: "pdf"}}};
    resetIndexes(api, "bench-a", mirrors, [preview]);
    return {files, mirrors, preview, task};
}

test("shared archive: three originals remain three cards and only the first has a PDF", async () => {
    const {api} = await loadApp();
    const {files, task} = workbookFixture(api);
    const materials = files.map((file) => api.normalizeMaterial(file, "input"));
    const merged = api.mergeIndexedMaterials(materials, task, "input");
    assert.deepEqual(Array.from(merged, (m) => m.name), files.map((f) => f.filename));
    const specs = merged.map((m) => api.resolvePreviewSpec(m, task, "input"));
    assert.equal(specs[0].kind, "pdf");
    for (const i of [1, 2]) {
        assert.equal(specs[i].previewBound, false);
        assert.equal(specs[i].kind, "missing");
        assert.equal(specs[i].mirrorUrl, `http://example.test/bench-monitor/assets/mirrors/${i + 1}_input.xlsx`);
    }
    assert.equal(api.mergeIndexedMaterials(merged, task, "input").length, 3);
});

test("duplicate declarations merge by source path, not by filename or content hash", async () => {
    const {api} = await loadApp();
    const {files, task} = workbookFixture(api);
    const materials = [files[0], {...files[0]}, ...files.slice(1)]
        .map((file) => api.normalizeMaterial(file, "input"));
    assert.equal(api.mergeIndexedMaterials(materials, task, "input").length, 3);
    const records = ["a/shared.xlsx", "b/shared.xlsx", "a/Shared.xlsx"].map((path) => ({
        bench_id: "bench-a", task_id: "task-1", role: "input", status: "ready",
        logical_path: path, sha256: "same-bytes", filename: path.split("/").pop(),
    }));
    resetIndexes(api, "bench-a", records);
    assert.equal(api.mergeIndexedMaterials([], task, "input").length, 3);
});

test("a conflicting preview hash cannot bind to a verified original", async () => {
    const {api} = await loadApp();
    const {files, mirrors, preview, task} = workbookFixture(api);
    resetIndexes(api, "bench-a", mirrors, [{...preview, source_sha256: "wrong-hash"}]);
    const spec = api.resolvePreviewSpec(api.normalizeMaterial(files[0], "input"), task, "input");
    assert.equal(spec.previewBound, false);
    assert.equal(spec.mirrorBound, true);
});

test("an explicit path conflict cannot be overridden by a shared URL or filename", async () => {
    const {api} = await loadApp();
    const {files, mirrors, task} = workbookFixture(api);
    const material = api.normalizeMaterial(files[0], "input");
    assert.equal(api.scoreIndexedRecord({...mirrors[0], logical_path: "another/1_input.xlsx"},
        task, material, "input"), -1);
});

test("ambiguous same-name originals never depend on index order", async () => {
    const {api} = await loadApp();
    const task = {id: "task-1", raw: {source: {files: [{filename: "shared.xlsx"}]}}};
    const records = ["a/shared.xlsx", "b/shared.xlsx"].map((path) => ({
        bench_id: "bench-a", task_id: "task-1", role: "input", status: "ready",
        filename: "shared.xlsx", logical_path: path, view_path: `assets/${path}`,
    }));
    for (const ordered of [records, [...records].reverse()]) {
        resetIndexes(api, "bench-a", ordered);
        const spec = api.resolvePreviewSpec(api.normalizeMaterial({filename: "shared.xlsx"}, "input"), task, "input");
        assert.equal(spec.mirrorBound, false);
    }
});

test("a previous task's archive preview cannot contaminate the next task", async () => {
    const {api} = await loadApp();
    const {files, mirrors, preview, task} = workbookFixture(api);
    resetIndexes(api, "bench-a", mirrors, [{...preview, task_id: "task-old",
        logical_path: "data/task-old/1_input.xlsx"}]);
    assert.equal(api.resolvePreviewSpec(api.normalizeMaterial(files[0], "input"), task, "input").previewBound, false);
});

test("human deliverables stay in output while input references and explicit dual use survive", async () => {
    const {api} = await loadApp();
    const input = {filename: "context.pdf", repository_path: "input/context.pdf"};
    const output = {filename: "answer.pdf", repository_path: "human/answer.pdf", role: "accepted_human_deliverable"};
    const task = {id: "task-1", raw: {source: {files: [input]},
        artifact: {status: "accepted_human_deliverable", files: [output]}}};
    const records = [input, output].map((file) => ({...file, bench_id: "bench-a", task_id: "task-1",
        logical_path: file.repository_path, role: "reference", status: "ready", view_path: `assets/${file.repository_path}`}));
    resetIndexes(api, "bench-a", records);
    const merged = api.mergeIndexedMaterials([api.normalizeMaterial(input, "input")], task, "input");
    assert.deepEqual(Array.from(merged, (m) => m.name), ["context.pdf"]);
    assert.equal(api.resolvePreviewSpec(api.normalizeMaterial(output, "output"), task, "output").mirrorBound, true);
    task.raw.source.files.push(output);
    assert.equal(api.mergeIndexedMaterials(task.raw.source.files.map((f) => api.normalizeMaterial(f, "input")), task, "input").length, 2);
});

test("late asset shards invalidate a previously missing material binding", async () => {
    const {api} = await loadApp();
    const {files, mirrors, preview, task} = workbookFixture(api);
    const material = api.normalizeMaterial(files[0], "input");
    resetIndexes(api, "bench-a");
    assert.equal(api.resolvePreviewSpec(material, task, "input").mirrorBound, false);
    resetIndexes(api, "bench-a", mirrors, [preview]);
    assert.equal(api.resolvePreviewSpec(material, task, "input").previewBound, true);
});

test("model-prefixed display names still bind their exact original download URL", async () => {
    const {api} = await loadApp();
    const file = {filename: "model-a · Report.pdf", url: "https://example.org/model-a/Report.pdf"};
    const task = {id: "task-1", raw: {artifact: {files: [file, {filename: "other.pdf"}]}}};
    const record = {bench_id: "bench-a", task_id: "task-1", role: "candidate", status: "ready",
        filename: "Report.pdf", logical_path: "model-a/Report.pdf", source_url: file.url, view_path: "assets/model-a/Report.pdf"};
    resetIndexes(api, "bench-a", [record]);
    assert.equal(api.resolvePreviewSpec(api.normalizeMaterial(file, "output"), task, "output").mirrorBound, true);
});

test("a missing runtime file must not bind the task card of the same task", async () => {
    const {api} = await loadApp();
    const file = {filename: "crackme.exe", repository_path: "tasks/example/input/crackme.exe"};
    const task = {id: "task-1", raw: {source: {files: [file]}}};
    const record = {bench_id: "bench-a", task_id: "task-1", role: "catalog", status: "ready",
        filename: "task_card.json", repository_path: "tasks/example/task_card.json", view_path: "assets/task_card.json"};
    resetIndexes(api, "bench-a", [record]);
    assert.equal(api.resolvePreviewSpec(api.normalizeMaterial(file, "input"), task, "input").mirrorBound, false);
});

test("an unnamed slot placeholder is replaced by its indexed files", async () => {
    const {api} = await loadApp();
    const raw = {status: "published_reports"};
    const task = {id: "task-1", raw: {artifact: raw}};
    const records = ["one.pdf", "two.pdf"].map((name) => ({
        bench_id: "bench-a", task_id: "task-1", role: "candidate", status: "ready",
        filename: name, logical_path: `reports/${name}`, view_path: `assets/${name}`,
    }));
    resetIndexes(api, "bench-a", records);
    const merged = api.mergeIndexedMaterials([api.normalizeMaterial(raw, "产物 1")], task, "output");
    assert.deepEqual(Array.from(merged, (m) => m.name), ["one.pdf", "two.pdf"]);
});

test("archive-container member aliases preserve extracted original bindings", async () => {
    const {api} = await loadApp();
    const file = {filename: "report.md", archive_path: "tasks/t/workspace.tar.gz::input/report.md"};
    const task = {id: "task-1", raw: {source: {files: [file]}}};
    const record = {bench_id: "bench-a", task_id: "task-1", role: "input", status: "ready",
        filename: "report.md", logical_path: "input/report.md", view_path: "assets/report.md"};
    resetIndexes(api, "bench-a", [record]);
    const material = api.normalizeMaterial(file, "input");
    assert.equal(api.resolvePreviewSpec(material, task, "input").mirrorBound, true);
    assert.equal(api.mergeIndexedMaterials([material], task, "input").length, 1);
    assert.equal(api.scoreIndexedRecord({...record, logical_path: "other.tar.gz::input/report.md"}, task, material, "input"), -1);
});
