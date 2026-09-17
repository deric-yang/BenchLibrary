# BenchList release · 2026-09-18

[Open BenchList](https://benchlibrary.com/#view=benchlist).

This release publishes the reviewed 2026-09-14 BenchList snapshot, including the
reference matrix, model coverage, monthly adoption trends and linked evidence.
It contains 127 benchmarks, 111 registered model releases, 88 counted models,
990 verified benchmark/model pairs and 38 public evidence images. Internal-only
fields and unverified claims are excluded by the public builder.

The public corpus is unchanged: 32 catalog entries, including 30 full benchmarks
and 10,161 task records. This release updates the UI and BenchList snapshot.

## Deployment identity

| Item | Value |
| --- | --- |
| Feature commit | `4a95580665de24058252796171d7806bbc7f7ee2` |
| R2 release | `20260918-benchlist-v4` |
| Worker version | `ca6ed6b0-f5f4-42a3-884c-fe356b493018` |
| Deployment | `070c209c-0828-436f-aa9c-c68b409140e2` |
| Traffic | 100% |
| Published at | 2026-09-17 21:11:18 UTC / 2026-09-18 05:11:18 Asia/Shanghai |
| Objects, including manifest | 102,677 |
| Total bytes | 20,611,118,228 |
| Manifest SHA-256 | `5c0797abdf145bc0cec2404700963c250fd5bf6a14ba9ca6aa48dd15845a58e1` |
| Worker module SHA-256 | `0d88265f5fceb8d8671f97c8fa7d7337573880845c07156e751316fbbbdd6733` |

The production Worker has exactly two bindings: `PUBLIC_CORPUS` and
`PUBLIC_RELEASE_ID`. The uploaded module was read back and compared byte for
byte before the Deployment API switched traffic. No production Wrangler deploy
was used. The temporary upload route and Worker were deleted and their absence
verified; the one-time upload credential was destroyed after inventory checks.

## Verification

- 168 Python tests and 82 Node tests passed.
- Export policy, reference closure and complete immutable export passed.
- Complete R2 inventory and independent offline verification passed.
- All 47 served site files (31,433,638 bytes), including all evidence images,
  matched their manifest SHA-256 over anonymous HTTPS.
- The complete manifest was downloaded over anonymous HTTPS and its SHA-256 matched.
- Reserved configuration paths return `400 Invalid site path` and are not served.
- The canonical anonymous public smoke passed: 5 benchmark families, 6 task probes,
  16 full object hashes, 4 pinned upstream anomalies, GameCraft contracts and index mappings.
- Browser checks passed: direct BenchList entry, 127/990 statistics, HLE 39/88,
  monthly HLE 15/25 in April, fullscreen trends, monthly evidence, loaded image,
  model pagination, return to the 32-entry catalog and 912 SpreadsheetBench V1 tasks.

The source commit identifies the deployed code and assets. A later documentation-only
commit recording this receipt does not change the immutable release.

## Rollback

The previous release is `20260911T103945Z-public-v3`. If rollback is necessary,
use the Deployment API to send 100% traffic to the preserved Worker version
`a1f90a03-1ac1-4b57-8737-e1ba4d6c726a`; do not overwrite either R2 release.

See [the release runbook](../RELEASE_RUNBOOK.md) and
[BenchList maintenance](../BENCHLIST.md).
