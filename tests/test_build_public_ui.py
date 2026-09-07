"""Tests for physical removal of private intake UI from public assets."""

from __future__ import annotations

import unittest

from scripts.build_public_ui import (
    assert_public_output,
    build_index,
    build_styles,
)


CLEAN_INDEX = """<!doctype html>
<html>
<head><meta name="robots" content="index, follow"></head>
<body>
<section class="bench-workspace"></section>
<script src="public-config.js" defer></script>
<script src="app.js" defer></script>
</body>
</html>
"""
CLEAN_CONFIG = '"use strict";\nglobalThis.KW_BENCH_PUBLIC_MODE = true;\n'


class PublicUiBuilderTest(unittest.TestCase):
    """Exercise public HTML removal, CSS filtering, and fail-closed scans."""

    def test_build_index_removes_entire_private_workspace(self) -> None:
        """The public HTML must not retain even an inert private placeholder."""
        source = """<!doctype html>
<html>
<head><meta name="robots" content="noindex, nofollow, noarchive"></head>
<body>
<button class="sidebar-ingestion-button" id="openIngestionSidebar">Add</button>
<button id="openIngestionHome">Add another</button>
<section class="ingestion-workspace hidden" id="ingestionWorkspace">
  <section><label>Contributor Key</label></section>
</section>
<section class="bench-workspace"></section>
    <script src="ingestion.js?v=private" defer></script>
    <script src="app.js?v=20260903a" defer></script>
</body>
</html>
"""

        result = build_index(source)

        self.assertNotIn("ingestion", result.lower())
        self.assertNotIn("Contributor", result)
        self.assertIn('<section class="bench-workspace">', result)
        self.assertIn('<meta name="robots" content="index, follow">', result)
        self.assertLess(result.index("public-config.js"), result.index("app.js"))

    def test_build_styles_filters_private_selectors_at_every_scope(self) -> None:
        """Shared selector groups keep public members inside nested at-rules."""
        source = """:root {
    --ink: #111;
}

.catalog-home,
.ingestion-workspace,
.bench-workspace {
    color: var(--ink);
}

@media (max-width: 960px) {
    .ingestion-layout,
    .task-layout {
        display: grid;
    }

    .ingestion-form-state[data-status="needs_input"] {
        color: orange;
    }
}

@keyframes public-pulse {
    0%, 100% {
        opacity: 1;
    }
}
"""

        result = build_styles(source)

        self.assertNotIn("ingestion", result.lower())
        self.assertNotIn("needs_input", result.lower())
        self.assertIn(".catalog-home", result)
        self.assertIn(".bench-workspace", result)
        self.assertIn(".task-layout", result)
        self.assertIn("@media (max-width: 960px)", result)
        self.assertIn("@keyframes public-pulse", result)
        self.assertEqual(result.count("{"), result.count("}"))

    def test_public_assertion_scans_every_deployable_surface(self) -> None:
        """Blocked intake vocabulary fails closed in HTML, JS, CSS, or config."""
        clean_surfaces = {
            "index": CLEAN_INDEX,
            "app": 'console.log("public catalog");\n',
            "styles": "body { color: #111; }\n",
            "config": CLEAN_CONFIG,
        }
        cases = (
            ("index", "Contributor Key"),
            ("app", "const route = 'ingestion';"),
            ("styles", '.state[data-status="needs-input"] {}'),
            ("config", "const credential = 'HF Token';"),
            ("app", "const credential = 'Hugging Face Token';"),
            ("app", "const endpoint = 'http://127.0.0.1:8913';"),
        )
        for surface, blocked_text in cases:
            with self.subTest(surface=surface, blocked_text=blocked_text):
                values = dict(clean_surfaces)
                values[surface] += blocked_text
                with self.assertRaises(ValueError):
                    assert_public_output(**values)

    def test_build_styles_rejects_malformed_source(self) -> None:
        """An unmatched CSS block must fail rather than emit partial output."""
        with self.assertRaisesRegex(ValueError, "unclosed CSS block"):
            build_styles(".catalog-home { color: black;")


if __name__ == "__main__":
    unittest.main()
