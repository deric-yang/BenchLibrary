"""Public BenchList must preserve evidence without disclosing internal source fields."""

from __future__ import annotations

import copy
import hashlib
import json
import unittest
from pathlib import Path

from scripts.build_public_benchlist import assert_public, public_data


class PublicBenchListTest(unittest.TestCase):
    """Validate the published dataset and negative disclosure cases."""

    def test_shipped_data_is_public_and_evidence_hashes_match(self) -> None:
        """Every published screenshot is referenced, hash-bound, and local to the bundle."""
        site = Path(__file__).resolve().parents[1] / "site"
        data = json.loads((site / "benchlist.json").read_text())
        assert_public(data)
        self.assertNotIn("sourceDocument", data)
        self.assertNotIn("snapshot", data["downloads"])
        self.assertEqual(len(data["benchmarks"]), 127)
        self.assertEqual(data["summary"]["confirmedReleasePairs"], 990)
        self.assertEqual(len(data["evidence"]), 38)
        used = set()
        for row in data["benchmarks"]:
            for field in ("originalModels", "originalDescription", "priority", "row", "valueReview"):
                self.assertNotIn(field, row)
            for claim in row["claimReviews"]:
                self.assertEqual(claim["status"], "confirmed")
                self.assertIn(claim["kind"], {"release_main", "release_appendix"})
                used.update(item["path"] for item in claim["evidence"])
        self.assertEqual(used, {item["path"] for item in data["evidence"]})
        for item in data["evidence"]:
            self.assertEqual(hashlib.sha256((site / item["path"]).read_bytes()).hexdigest(), item["sha256"])

    def test_export_ignores_private_snapshot_and_unverified_claims(self) -> None:
        """Public output cannot inherit internal fields by accidental object spreading."""
        site = Path(__file__).resolve().parents[1] / "site"
        source = json.loads((site / "benchlist.json").read_text())
        source["sourceDocument"] = {"url": "https://ku.baidu-int.com/private"}
        for row in source["benchmarks"]:
            row["originalDescription"] = "private snapshot"
            row["priority"] = "P0"
            for claim in row["claimReviews"]:
                for evidence in claim["evidence"]:
                    evidence["path"] = "data/" + evidence["path"]
        for evidence in source["evidence"]:
            evidence["path"] = "data/" + evidence["path"]
        rejected = copy.deepcopy(source["benchmarks"][0]["claimReviews"][0])
        rejected["status"] = "unverified"
        rejected["sourceUrl"] = "https://ku.baidu-int.com/private"
        source["benchmarks"][0]["claimReviews"].append(rejected)
        data = public_data(source)
        self.assertNotIn("private snapshot", json.dumps(data))
        self.assertNotIn("baidu-int.com", json.dumps(data))

    def test_nested_private_and_active_urls_fail_closed(self) -> None:
        """A reviewed field is still rejected if it contains a private or executable URL."""
        for value in ("https://ku.baidu-int.com/private", "http://10.25.66.233/", "javascript:alert(1)"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                assert_public({"evidence": [{"url": value}]})


if __name__ == "__main__":
    unittest.main()
