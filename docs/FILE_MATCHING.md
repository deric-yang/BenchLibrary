# File identity and preview binding

File cards represent originals, not preview derivatives. Repository paths and archive members identify originals; a shared archive or dataset URL is provenance only. A preview must agree with its original's path and available source hash. Ambiguous candidates must not be resolved by index order.

The file-list merge preserves case-sensitive paths, distinct directories and explicitly declared dual-use files. It recognizes archive-container/member aliases, refreshes bindings after lazy index loads, and excludes declared human deliverables from automatic input synthesis. Model-prefixed display labels still resolve through their original download URLs.

Regression tests live in [file-merge.test.mjs](../test/file-merge.test.mjs) and run with npm test. The SpreadsheetBench V1 three-workbook fixture produces three cards; only the workbook with its own PDF gets that preview. Other workbooks retain their original download links. Separate tests cover role separation, conflicting hashes, ambiguous filenames, lazy loading, case-sensitive paths and archive member aliases.

The original-file download action remains distinct from the PDF viewer's download action. Missing previews do not imply missing originals.
