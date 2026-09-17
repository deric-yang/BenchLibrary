"""Export reviewed public BenchList evidence without the internal source snapshot."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlsplit


PRIVATE_TEXT = re.compile(r"baidu-int\.com|10\.(?:\d{1,3}\.){2}\d{1,3}|/mnt/data/|/Users/|/home/")
CLAIM_FIELDS = (
    "model", "status", "kind", "sourceUrl", "sourceTitle", "location", "provider", "checkedAt",
    "countingModel", "releaseDate", "releaseDateRange", "inScope", "exclusionReason", "evidence",
)
ROW_FIELDS = ("id", "category", "name", "recommendedDescription", "descriptionSources", "isAddition")
MODEL_FIELDS = (
    "model", "provider", "releaseDate", "releaseDateRange", "dateSources", "aliases", "countingModel",
    "eligible", "exclusionReason", "scopeNote",
)


def selected(value: dict, keys: tuple[str, ...]) -> dict:
    """Copy only explicitly reviewed schema fields."""
    return {key: value[key] for key in keys if key in value}


def assert_public(value: object) -> None:
    """Reject private locations, unsafe URLs, and unexpected local paths."""
    if isinstance(value, dict):
        for item in value.values():
            assert_public(item)
    elif isinstance(value, list):
        for item in value:
            assert_public(item)
    elif isinstance(value, str):
        if PRIVATE_TEXT.search(value):
            raise ValueError("Private location in public BenchList")
        if re.match(r"^[a-z][a-z0-9+.-]*://|^(?:javascript|data|file):", value, re.I):
            url = urlsplit(value)
            if url.scheme != "https" or not url.hostname or url.username or url.password:
                raise ValueError("Non-public URL in BenchList")


def public_data(source: dict) -> dict:
    """Preserve verified release counts while dropping internal hypotheses and priorities."""
    rows = []
    used = set()
    for original in source["benchmarks"]:
        row = selected(original, ROW_FIELDS)
        row["claimReviews"] = []
        for claim in original.get("claimReviews", []) + original.get("additionalCitations", []):
            if claim.get("status") != "confirmed" or claim.get("kind") not in {"release_main", "release_appendix"}:
                continue
            if not str(claim.get("sourceUrl", "")).startswith("https://"):
                raise ValueError("Verified release claim lacks a public source")
            clean = selected(claim, CLAIM_FIELDS)
            clean["evidence"] = []
            for evidence in claim.get("evidence", []):
                path = evidence["path"]
                if not re.fullmatch(r"data/benchlist-evidence/[A-Za-z0-9._-]+", path):
                    raise ValueError("Unexpected evidence path")
                used.add(path)
                item = selected(evidence, ("path", "caption", "sourceUrl"))
                item["path"] = path.removeprefix("data/")
                clean["evidence"].append(item)
            row["claimReviews"].append(clean)
        rows.append(row)
    evidence = []
    for item in source["evidence"]:
        if item["path"] in used:
            clean = selected(item, ("path", "caption", "sourceUrl", "sha256"))
            clean["path"] = item["path"].removeprefix("data/")
            evidence.append(clean)
    if {"data/" + item["path"] for item in evidence} != used:
        raise ValueError("Evidence is absent from the reviewed hash inventory")
    scope = dict(source["modelScope"])
    scope["scopeNote"] = "13 家厂商的通用、推理、代码及多模态理解模型；不纳入纯生成、embedding 或量化副本。"
    result = {
        "schemaVersion": source["schemaVersion"], "title": "BenchList · 模型发布引用审计",
        "checkedAt": source["checkedAt"], "publicEdition": True, "modelScope": scope,
        "modelRegistry": [selected(item, MODEL_FIELDS) for item in source["modelRegistry"]],
        "providersChecked": source["providersChecked"],
        "methodology": [
            "仅计入有第一方来源的自身发布正文或附录证据；对照列和第三方结果不增加计数。",
            "按统计模型去重；GPT-5.6 变体合并，GPT-6 独立。没有证据不代表未参评。",
            "模型覆盖率分母包括窗口内未取得引用证据的模型；月度趋势按实际型号发布日期归月。",
            "这是人工核验快照，日期未自动滚动；引用频次不代表性能得分。",
        ],
        "summary": selected(source["summary"], (
            "totalBenchmarks", "addedBenchmarks", "confirmedReleasePairs", "models", "providers",
            "registeredReleases", "inScopeReleases", "excludedReleases", "unconfirmedDates",
        )),
        "benchmarks": rows, "evidence": evidence,
        "downloads": {"json": "benchlist.json", "markdown": "benchlist-audit.md"},
    }
    result["summary"]["screenshotFiles"] = len(evidence)
    assert_public(result)
    return result


def export(source_root: Path, output: Path) -> dict:
    """Write public JSON, a public report, and hash-checked source screenshots."""
    source = json.loads((source_root / "data/benchlist.json").read_text())
    data = public_data(source)
    output.mkdir(parents=True, exist_ok=True)
    for evidence in data["evidence"]:
        original = source_root / "data" / evidence["path"]
        if original.is_symlink() or not original.is_file():
            raise ValueError("Evidence must be a regular file")
        payload = original.read_bytes()
        if hashlib.sha256(payload).hexdigest() != evidence["sha256"]:
            raise ValueError("Evidence SHA-256 mismatch")
        target = output / evidence["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    (output / "benchlist.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    lines = ["# BenchList · 公开发布引用审计", "", f"核验日期：{data['checkedAt']}。", ""]
    lines += data["methodology"] + [""]
    for row in data["benchmarks"]:
        lines += [f"## {row['name']}", "", row.get("recommendedDescription", ""), ""]
        for claim in row["claimReviews"]:
            lines.append(f"- {claim['model']}：[发布来源]({claim['sourceUrl']}) · {claim.get('location', '')}")
        lines.append("")
    report = "\n".join(lines)
    if PRIVATE_TEXT.search(report):
        raise ValueError("Private location in report")
    (output / "benchlist-audit.md").write_text(report)
    return data["summary"]


def main() -> None:
    """Build a public edition from an explicitly selected internal snapshot."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(export(args.source, args.output), ensure_ascii=False))


if __name__ == "__main__":
    main()
