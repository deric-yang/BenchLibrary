# File identity and preview binding release · 2026-09-20

[Open the reported task](https://benchlibrary.com/#bench=spreadsheetbench-v1&task=spreadsheetbench-v1--13-1).

This release merges file declarations, mirrors and previews by original-file identity.
SpreadsheetBench V1 task 13-1 now shows three input workbooks instead of five cards.
Each download points to its own original XLSX. Workbooks 2 and 3 have no converted
preview yet and display an explicit original-download fallback. A requested PDF
conversion no longer causes raw Office bytes to be embedded as a PDF.

The shared matching logic also rejects conflicting paths/hashes and ambiguous ties,
preserves archive-member identities, and keeps declared outputs out of inferred inputs.
See [file matching](../FILE_MATCHING.md).

## Deployment identity

| Item | Value |
| --- | --- |
| Code commit | `d600942b437e012dd55e92350bd00da3709392d8` |
| R2 release | `20260919-file-merge-v5` |
| Worker version | `fe523fce-f498-4bbb-9785-55d8c1e3a370` |
| Deployment | `92549d83-8405-48f7-ad8e-1a7e5bbfb38e` |
| Traffic | 100% |
| Published at | 2026-09-20 02:01:26 UTC / 2026-09-20 10:01:26 Asia/Shanghai |
| Objects, including manifest | 102,677 |
| Total bytes | 20,611,226,634 |
| Manifest SHA-256 | `65d3bea82d5419a3d48a5d72e9ace46d112dbae4215c33f5b3f79d1a25d85f95` |
| Public app SHA-256 | `a5c5debb7bcc516400dc953f83694524b59cb95e65f0a0f1ce10ca8358f45349` |
| Worker module SHA-256 | `0d88265f5fceb8d8671f97c8fa7d7337573880845c07156e751316fbbbdd6733` |
| Policy SHA-256 | `9630b50e4f9bed8e74146994919b7b7b512e26f94f6b73266382313993657de2` |
| Audited data source | `20260911T032552Z-6f7a94026d79-public-v3-indexed-audited` |
| Internal UI release | `root-ui-20260919T152415Z-59054-12318-220134f3e8fb` |

The public corpus remains 32 catalog entries, 30 full benchmarks and 10,161 tasks.
The existing BenchList snapshot is preserved. There are no added or removed payload
paths compared with the preceding public release.

## Verification

- 133 Node tests passed: 39 internal UI tests and 94 public UI/Worker tests.
- 168 Python tests passed; the public UI build and Wrangler dry-run passed.
- Export policy, complete reference closure and full immutable export checks passed.
- Complete R2 inventory and independent offline verification matched every object,
  size, SHA-256 and HTTP metadata field.
- The uploaded production module was read back and compared byte for byte. Runtime
  settings and exactly two bindings (`PUBLIC_CORPUS`, `PUBLIC_RELEASE_ID`) were verified.
- Deployment used the Version Upload and Deployment APIs, without production Wrangler deploy.
- The one-time upload key was retired after inventory verification. The temporary
  route and Worker were deleted; route absence and Worker nonexistence were verified.
- Anonymous HTTPS downloads of the deployed app and all three reported XLSX files
  matched their expected SHA-256; the workbooks have the XLSX content type.
- Browser checks confirmed three input cards, correct original links for workbooks
  2 and 3, task search, English requirement text, and input/output tab separation.
- The canonical anonymous smoke passed for five benchmark families and six task
  probes, including 16 complete object hashes, four pinned upstream anomalies,
  GameCraft contracts, and mirror/preview index mappings.
- BenchList loaded with its preserved 127 entries and 990 verified references.
- The internal matching audit covered 36 benchmarks and 13,815 tasks. The public
  targeted replay covered 972 V1, RLI and WorkBuddy tasks with zero duplicate cards,
  preview/path conflicts, output leakage or unexplained binding loss. This targeted
  replay is not a claim of browser coverage or full public-dataset replay.

The receipt is a later documentation-only commit; the code commit above identifies
the immutable deployed code. Missing converted previews were not generated in this release.

## Rollback

The previous release is `20260918-benchlist-v4`, with deployment
`070c209c-0828-436f-aa9c-c68b409140e2`. To roll back, use the Deployment API to send
100% traffic to preserved Worker version `ca6ed6b0-f5f4-42a3-884c-fe356b493018`.
Do not overwrite either R2 release. See [the release runbook](../RELEASE_RUNBOOK.md).
