# Activities release · 2026-09-29

[Open Activities](https://benchlibrary.com/activities/). The third navigation entry after
BenchList opens a six-slide VibeMotionBench presentation with five playable videos.
All presentation files and media are served from this public site, with no intranet dependencies.

| Item | Value |
| --- | --- |
| Code commit | `a08132d549a9a410319a00b8e9c29387c11755ff` |
| Preserved corpus release | `20260919-file-merge-v5` |
| Site overlay release | `20260929-activities-v1` |
| Worker version | `0778de66-2519-4b91-a33e-b19a7145d648` |
| Deployment | `10b9fa9f-c010-46da-b0f1-328af242a9fa` |
| Traffic | 100% |
| Published | 2026-09-29 07:03:34 UTC / 15:03:34 Asia/Shanghai |
| New/changed objects | 19 |
| Incremental bytes | 27,124,134 |
| Previous Worker version | `fe523fce-f498-4bbb-9785-55d8c1e3a370` |

The original 32 benchmarks, 10,161 tasks and BenchList data remain in their existing,
verified R2 release. No corpus objects were copied or uploaded. The exact incremental
object list is `config/activity_release.json`; see [Activities maintenance](../ACTIVITIES.md).

## Validation

- 98 Node tests and 4 public UI builder tests passed.
- Complete incremental R2 inventory matched all 19 paths, lengths, SHA-256 values and HTTP metadata;
  an independent local check also matched the inventory.
- Both production modules were read back and compared byte for byte; runtime settings and
  exactly two bindings were verified before the guarded Deployment API switch.
- Browser checks covered desktop and narrow layouts, homepage → Activities → BenchList/catalog,
  all five videos decoding at 1920px width, and native video fullscreen.
- Anonymous HTTPS downloads matched the complete SHA-256 and size of all 19 new/changed files (27,124,134 bytes).
- HTTP Range returned correct 206 responses and original leading bytes for all five videos.
- Temporary upload route and Worker were deleted and their absence verified; the one-time key was retired.

## Module hashes

- `src/index.js`: `f0b5321b7f0c1c61c8f2ee336631f9eefac314d8c9e454d20077088415f4198b`
- `src/site-overlay.js`: `12fade7b9806b1b19d0661ffb26112bdd848da8b711097e9b5cba764c6f7c68a`

## Rollback

Send 100% traffic to preserved Worker version `fe523fce-f498-4bbb-9785-55d8c1e3a370`
using the Deployment API. Preserve both R2 prefixes; do not overwrite immutable objects.
This receipt is a later documentation-only commit.
