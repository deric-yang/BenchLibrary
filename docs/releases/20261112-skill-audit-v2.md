# Complete Skill audit activity — 2026-11-12

Published at https://benchlibrary.com/activities/skill-audit/ with an entry in /activities/. The owner explicitly authorized public access and complete concrete case material. All 43 cases include original questions and answers, complete diagnoses and adjudications, historical judge labels/reasons, and all 300 structured business events used for attribution (160 model requests). Source business content is not paraphrased or newly redacted; 14 pre-existing credential placeholders remain intact. Raw binary Trace archives remain on the Devbox.

Case JSON files are artifact data held only on the Devbox and R2, excluded from Git. Repository configuration pins their paths, sizes, and hashes. Browser rendering uses textContent; evidence does not execute embedded markup or fetch internal links. Each case payload is hash-checked before rendering. Mobile reading, filtering, search, deep links, downloads, and dark mode are supported.

## Immutable deployment

- Source code commit: a056e07a24b4dfb2d4819513dbe57538b4df79f5
- Corpus release, unchanged: 20260919-file-merge-v5
- Site overlay: 20261112-skill-audit-v2
- R2 closure: 67 objects, 45,218,301 bytes, including its manifest.
- Public UI/data objects: 66, 45,187,856 bytes.
- R2 inventory SHA-256: c4c15ebf7fc63b5de89f653421c11b4b543c08332def11097f03a56c44e73fd9
- Previous Worker version (exact rollback anchor): 0778de66-2519-4b91-a33e-b19a7145d648
- New Worker version: 671e91c0-c693-4ba7-9dd1-3d2a7ba59943
- Deployment: 41b9f781-0542-41d7-86f5-de9e8532e3a7, 100%, created 2026-11-12T09:57:47.91403Z.
- Runtime: 2026-09-06, nodejs_compat, standard.
- Exact two bindings preserved: PUBLIC_CORPUS → benchlibrary-public; PUBLIC_RELEASE_ID → 20260919-file-merge-v5.
- worker.mjs SHA-256: 9d8ca8ff718e56094540d068473e6c8f097852230c544ef3b0df7f61893d9868
- site-overlay.js SHA-256: 915a8adef325a98a802abc3d2fdba9bcb1ad53238bc0dd654424b875f60cfee6

Both uploaded modules were read back from the exact new version and compared byte-for-byte to committed source before traffic switched. R2 inventory covered every object and its HTTP metadata. The one-time key was destroyed, then the temporary route and uploader Worker were removed. Final control-plane readback confirmed no temporary routes and the expected version at 100%.

The superseded summary-only v1 was stopped before any R2 upload or production switch. Its temporary write surface and credential were removed. V2 is the first live Skill audit publication.

## Validation

- 101 Node tests; 168 Python tests from the same unchanged Python tooling; git diff checks; Wrangler local dry run passed. Production deployment used Version Upload and Deployment APIs.
- Source equality checked for every case's structured trajectory, historical evaluation, provenance, initial diagnosis, and effective diagnosis.
- Anonymous readback: all 66 public objects matched actual bytes and SHA-256; both canonical slash redirects passed.
- All 43 case payloads loaded and verified in a real browser, with no message reconstruction errors or page errors.
- Mobile overview, expanded case and trajectory had no horizontal overflow. Search, category filters, deep links, and dark mode passed.
- All five existing VibeMotionBench videos passed Range checks; original activity entry remains.
- Anonymous corpus smoke passed across five benchmark families, including task counts, mappings, representative originals/previews, Gold and Verifier contracts, and four registered upstream anomalies.
- Initial live browser assertion rejected Cloudflare's automatically injected beacon request attempts. Targeted comparison confirmed identical existing behavior on the previous activity: CSP blocks the script and no external response occurs. The corrected live assertion requires exactly that outcome and passed; the original failing receipt is retained.
- The pinned development dependency audit reported four high findings. Dependencies were not changed; deployed Worker modules are the two directly verified vanilla modules.

Historical attribution and new V0 reruns remain separately counted. This publication does not change the Skill, validation set, merchant execution, or model routing. It establishes no Skill improvement claim.
