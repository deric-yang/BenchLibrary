#!/usr/bin/env python3
"""Build the credential-free public UI from the internal Bench Monitor UI.

The internal source remains the canonical UI. This builder copies the shared
catalog experience while physically removing every ingestion control and the
ingestion client from the deployable public site.
"""

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path


BLOCKED_PUBLIC_TEXT = (
    "Contributor Key",
    "HF Token",
    ":8913",
    "ingestion.js",
)


def replace_once(text: str, old: str, new: str, *, label: str) -> str:
    """Replace exactly one known source fragment, failing loudly on drift."""
    count = text.count(old)
    if count != 1:
        raise ValueError(f"expected one {label} fragment, found {count}")
    return text.replace(old, new, 1)


def regex_replace_once(
    text: str,
    pattern: str,
    replacement: str,
    *,
    label: str,
) -> str:
    """Replace exactly one regex match, failing loudly on source drift."""
    result, count = re.subn(pattern, replacement, text, count=1, flags=re.DOTALL)
    if count != 1:
        raise ValueError(f"expected one {label} fragment, found {count}")
    return result


def build_index(source: str) -> str:
    """Remove private controls and add public runtime configuration."""
    html = source
    for element_id in ("openIngestionSidebar", "openIngestionHome"):
        html = regex_replace_once(
            html,
            rf"\s*<button\b[^>]*\bid=[\"']{element_id}[\"'][^>]*>.*?</button>",
            "",
            label=element_id,
        )

    html = regex_replace_once(
        html,
        r"\n\s*<section\s+class=[\"']ingestion-workspace\s+hidden[\"']\s+"
        r"id=[\"']ingestionWorkspace[\"'][^>]*>.*?</section>\s*"
        r"(?=<section\s+class=[\"']bench-workspace)",
        (
            "\n            <section class=\"ingestion-workspace hidden\" "
            "id=\"ingestionWorkspace\" aria-hidden=\"true\"></section>\n\n            "
        ),
        label="ingestion workspace",
    )
    html = regex_replace_once(
        html,
        r"\n\s*<script\s+src=[\"']ingestion\.js(?:\?[^\"']*)?[\"']\s+defer></script>",
        "",
        label="ingestion script",
    )
    html = replace_once(
        html,
        '    <script src="app.js?v=20260903a" defer></script>',
        (
            '    <script src="public-config.js" defer></script>\n'
            '    <script src="app.js" defer></script>'
        ),
        label="application script",
    )
    html = replace_once(
        html,
        '<meta name="robots" content="noindex, nofollow, noarchive">',
        '<meta name="robots" content="index, follow">',
        label="robots metadata",
    )
    html = html.replace("本地镜像预览站", "公开镜像预览站")
    html = html.replace(
        "LIVE RESEARCH INDEX · LOCAL ARTIFACT MIRRORS",
        "PUBLIC RESEARCH INDEX · PUBLISHED ARTIFACT MIRRORS",
    )
    public_copy = {
        "正在读取本地审计": "正在读取公开审计",
        "本地 / 公开": "站内镜像 / 公开",
        "任务要求、输入、Verifier 与本地产物预览会在这里展开。": (
            "任务要求、输入、Verifier 与站内产物预览会在这里展开。"
        ),
    }
    for internal_text, public_text in public_copy.items():
        html = html.replace(internal_text, public_text)
    return html


def build_app(source: str) -> str:
    """Install public-mode guards without changing the catalog experience."""
    app = replace_once(
        source,
        '"use strict";\n',
        (
            '"use strict";\n\n'
            "const PUBLIC_MODE = globalThis.KW_BENCH_PUBLIC_MODE === true;\n"
        ),
        label="strict-mode preamble",
    )

    app = replace_once(
        app,
        """    dom.openIngestionHome.addEventListener("click", () => {
        showIngestionWorkspace({updateLocation: true});
    });
    dom.openIngestionSidebar.addEventListener("click", () => {
        showIngestionWorkspace({updateLocation: true});
    });
    dom.ingestionBackButton.addEventListener("click", () => {
        showCatalogHome();
    });
""",
        """    if (!PUBLIC_MODE) {
        dom.openIngestionHome?.addEventListener("click", () => {
            showIngestionWorkspace({updateLocation: true});
        });
        dom.openIngestionSidebar?.addEventListener("click", () => {
            showIngestionWorkspace({updateLocation: true});
        });
        dom.ingestionBackButton?.addEventListener("click", () => {
            showCatalogHome();
        });
    }
""",
        label="ingestion event bindings",
    )

    app = replace_once(
        app,
        """function showIngestionWorkspace(options = {}) {
    state.activeBenchId = "";
""",
        """function showIngestionWorkspace(options = {}) {
    if (PUBLIC_MODE) {
        showCatalogHome({
            scroll: options.scroll,
            updateLocation: options.updateLocation,
        });
        return;
    }
    state.activeBenchId = "";
""",
        label="ingestion workspace guard",
    )
    app = replace_once(
        app,
        """function isIngestionLocation() {
    const params = new URLSearchParams(location.hash.replace(/^#/, ""));
    return params.get("view") === "ingestion";
}
""",
        """function isIngestionLocation() {
    if (PUBLIC_MODE) {
        return false;
    }
    const params = new URLSearchParams(location.hash.replace(/^#/, ""));
    return params.get("view") === "ingestion";
}
""",
        label="ingestion location guard",
    )
    app = replace_once(
        app,
        """    if (view === "ingestion") {
        showIngestionWorkspace({
            jobId: params.get("job") || "",
            scroll: false,
            updateLocation: false,
        });
        return;
    }
""",
        """    if (view === "ingestion") {
        if (PUBLIC_MODE) {
            updateLocation("", "");
            if (state.benches.length) {
                showCatalogHome({scroll: false, updateLocation: false});
            }
            return;
        }
        showIngestionWorkspace({
            jobId: params.get("job") || "",
            scroll: false,
            updateLocation: false,
        });
        return;
    }
""",
        label="ingestion hash handling",
    )
    app = replace_once(
        app,
        """function updateIngestionLocation(jobId) {
    const params = new URLSearchParams();
""",
        """function updateIngestionLocation(jobId) {
    if (PUBLIC_MODE) {
        updateLocation("", "");
        return;
    }
    const params = new URLSearchParams();
""",
        label="ingestion history guard",
    )

    public_copy = {
        "目录暂不可用 · 接入仍可使用": "目录暂不可用",
        "本地审计文件读取失败": "公开审计文件读取失败",
        "本地镜像覆盖": "站内镜像覆盖",
        "本地审计读取失败": "公开审计读取失败",
        "正在读取本地审计": "正在读取公开审计",
        "本地 / 可索引公开": "站内镜像 / 可索引公开",
        "等待本地镜像索引": "等待站内镜像索引",
        "HF 授权内网镜像 · 问题可审阅，答案已排除": (
            "HF 授权数据 · 可公开问题可审阅，答案已排除"
        ),
        "浏览器不会携带 Hugging Face Token": "本站不会代用户访问 Hugging Face 门禁数据",
        "文件与本地预览": "文件与站内预览",
        "本站本地镜像优先": "本站镜像优先",
        "正在校验本地预览": "正在校验站内预览",
        "本地预览地址已失效": "站内预览地址已失效",
        "没有可读取的本地文本镜像": "没有可读取的站内文本镜像",
        "本地预览正在补齐": "站内预览正在补齐",
        "文件已物化到受保护语料库": "来源文件受许可限制，公开版未分发",
        (
            "开发机已保存并校验原始文件；由于格式、许可或安全边界，"
            "本站暂不公开原件，也没有可安全内嵌的预览。"
        ): (
            "来源记录显示文件已保存并校验；由于格式、许可或安全边界，"
            "公开版不提供原件或可内嵌预览。"
        ),
        "这个 Bench 已有本地镜像": "这个 Bench 已有站内镜像",
        "等待本地镜像与转换结果": "等待站内镜像与转换结果",
        (
            "当前没有本地配置正文；待镜像后会在此显示，而不是只给出跳转按钮。"
        ): (
            "当前没有站内配置正文；公开镜像补齐后会在此显示，而不是只给出跳转按钮。"
        ),
        "Benchmark 接入工作台": "评测目录",
        "本地镜像已就绪": "站内镜像已就绪",
    }
    for internal_text, public_text in public_copy.items():
        app = app.replace(internal_text, public_text)
    return app


def assert_public_output(index: str, app: str, config: str) -> None:
    """Verify that the generated deploy surface cannot expose intake secrets."""
    combined = "\n".join((index, app, config))
    for blocked in BLOCKED_PUBLIC_TEXT:
        if blocked in combined:
            raise ValueError(f"public output contains blocked text: {blocked}")

    forbidden_ids = (
        "openIngestionHome",
        "openIngestionSidebar",
        "ingestionBackButton",
        "ingestionForm",
        "contributorKey",
        "ingestionHfToken",
    )
    for element_id in forbidden_ids:
        if f'id="{element_id}"' in index:
            raise ValueError(f"public HTML contains private control: {element_id}")

    placeholder = (
        '<section class="ingestion-workspace hidden" '
        'id="ingestionWorkspace" aria-hidden="true"></section>'
    )
    if index.count(placeholder) != 1:
        raise ValueError("public HTML must retain exactly one inert workspace placeholder")
    if "KW_BENCH_PUBLIC_MODE = true" not in config:
        raise ValueError("public runtime flag is missing")
    if "const PUBLIC_MODE" not in app or "if (PUBLIC_MODE)" not in app:
        raise ValueError("public-mode application guards are missing")
    if 'params.get("view") || ""' not in app or 'view === "ingestion"' not in app:
        raise ValueError("legacy ingestion hash redirect is missing")
    if index.find("public-config.js") > index.find("app.js"):
        raise ValueError("public mode must be configured before app.js")
    if "noindex" in index or "nofollow" in index:
        raise ValueError("public page still opts out of indexing")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "bench_monitor",
        help="path to the internal Bench Monitor UI",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "site",
        help="public static output directory",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source_dir = args.source.resolve()
    output_dir = args.output.resolve()
    required = ("index.html", "app.js", "styles.css")
    missing = [name for name in required if not (source_dir / name).is_file()]
    if missing:
        raise FileNotFoundError(f"missing UI source files: {', '.join(missing)}")

    output_dir.mkdir(parents=True, exist_ok=True)
    config_path = output_dir / "public-config.js"
    if not config_path.is_file():
        raise FileNotFoundError(f"missing public runtime config: {config_path}")

    index = build_index((source_dir / "index.html").read_text(encoding="utf-8"))
    app = build_app((source_dir / "app.js").read_text(encoding="utf-8"))
    config = config_path.read_text(encoding="utf-8")
    assert_public_output(index, app, config)

    (output_dir / "index.html").write_text(index, encoding="utf-8")
    (output_dir / "app.js").write_text(app, encoding="utf-8")
    shutil.copyfile(source_dir / "styles.css", output_dir / "styles.css")
    print(f"Built public UI in {output_dir}")


if __name__ == "__main__":
    main()
