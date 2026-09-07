#!/usr/bin/env python3
"""Build the credential-free public UI from the internal Bench Monitor UI.

The internal source remains the canonical UI. This builder copies the shared
catalog experience while physically removing every ingestion control and the
ingestion client from the deployable public site.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


BLOCKED_PUBLIC_PATTERNS = (
    ("internal intake identifier", re.compile(r"ingestion", re.IGNORECASE)),
    ("contributor credential", re.compile(r"contributor", re.IGNORECASE)),
    ("manual-input state", re.compile(r"needs(?:_|-)input", re.IGNORECASE)),
    ("HF token", re.compile(r"\bhf[\s_-]*token\b", re.IGNORECASE)),
    ("Hugging Face token", re.compile(r"hugging\s+face\s+token", re.IGNORECASE)),
    ("internal API port", re.compile(r":8913\b")),
)

NESTED_CSS_AT_RULES = (
    "@container",
    "@document",
    "@keyframes",
    "@layer",
    "@media",
    "@scope",
    "@supports",
    "@-webkit-keyframes",
)


def find_blocked_public_text(text: str) -> tuple[str, str] | None:
    """Return the first blocked label and source spelling in ``text``."""
    for label, pattern in BLOCKED_PUBLIC_PATTERNS:
        match = pattern.search(text)
        if match:
            return label, match.group(0)
    return None


def find_css_open_brace(source: str, start: int) -> int | None:
    """Find the next CSS block opener outside strings and comments."""
    quote = ""
    escaped = False
    in_comment = False
    index = start
    while index < len(source):
        char = source[index]
        following = source[index + 1] if index + 1 < len(source) else ""
        if in_comment:
            if char == "*" and following == "/":
                in_comment = False
                index += 2
                continue
        elif quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = ""
        elif char == "/" and following == "*":
            in_comment = True
            index += 2
            continue
        elif char in ('"', "'"):
            quote = char
        elif char == "{":
            return index
        index += 1
    return None


def find_css_close_brace(source: str, opening: int) -> int:
    """Find the closing brace paired with ``opening`` in CSS source."""
    quote = ""
    escaped = False
    in_comment = False
    depth = 0
    index = opening
    while index < len(source):
        char = source[index]
        following = source[index + 1] if index + 1 < len(source) else ""
        if in_comment:
            if char == "*" and following == "/":
                in_comment = False
                index += 2
                continue
        elif quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = ""
        elif char == "/" and following == "*":
            in_comment = True
            index += 2
            continue
        elif char in ('"', "'"):
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
        index += 1
    raise ValueError(f"unclosed CSS block at offset {opening}")


def css_indent(leading: str) -> str:
    """Return the indentation encoded at the end of leading whitespace."""
    if "\n" not in leading:
        return leading
    return leading.rsplit("\n", 1)[1]


def sanitize_css_scope(source: str) -> str:
    """Remove private selectors from one CSS rule scope."""
    output: list[str] = []
    cursor = 0
    while cursor < len(source):
        opening = find_css_open_brace(source, cursor)
        if opening is None:
            output.append(source[cursor:])
            break
        closing = find_css_close_brace(source, opening)
        prelude = source[cursor:opening]
        leading_match = re.match(r"\s*", prelude)
        leading = leading_match.group(0) if leading_match else ""
        header = prelude[len(leading):].strip()
        body = source[opening + 1:closing]
        if not header:
            raise ValueError(f"CSS block at offset {opening} has no selector")

        lowered_header = header.lower()
        if lowered_header.startswith("@"):
            nested = lowered_header.startswith(NESTED_CSS_AT_RULES)
            sanitized_body = sanitize_css_scope(body) if nested else body
            output.append(f"{leading}{header} {{{sanitized_body}}}")
        else:
            selectors = [selector.strip() for selector in header.split(",")]
            public_selectors = [
                selector
                for selector in selectors
                if selector and find_blocked_public_text(selector) is None
            ]
            if public_selectors:
                separator = ",\n" + css_indent(leading)
                selector_group = separator.join(public_selectors)
                output.append(f"{leading}{selector_group} {{{body}}}")
            else:
                output.append(leading.rstrip(" \t"))
        cursor = closing + 1
    return "".join(output)


def build_styles(source: str) -> str:
    """Remove all private intake selectors from the shared stylesheet."""
    styles = sanitize_css_scope(source)
    blocked = find_blocked_public_text(styles)
    if blocked:
        label, spelling = blocked
        raise ValueError(f"public CSS contains blocked {label}: {spelling}")
    return styles


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
        "\n\n            ",
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
    """Physically remove the internal intake client from the public application."""
    app = source
    app = replace_once(
        app,
        """        "jumpToAudit", "openIngestionHome", "openIngestionSidebar", "heroTrackedCount",
        "knowledgeCoverage", "knowledgeCoverageStatus", "ingestionWorkspace",
        "ingestionBackButton",
""",
        """        "jumpToAudit", "heroTrackedCount", "knowledgeCoverage",
        "knowledgeCoverageStatus",
""",
        label="private DOM registry",
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
        "",
        label="private event bindings",
    )
    app = replace_once(
        app,
        """    if (isIngestionLocation()) {
        dom.loadingLayer.classList.add("hidden");
        setNavStatus("loading", "目录后台加载");
    }
    else {
        showLoader({
            kicker: "CATALOG · STAGE 1 / 2",
            title: "正在打开评测目录",
            message: "先读取轻量索引；题库只在你选择 Bench 后加载。",
        });
        setNavStatus("loading", "读取目录");
    }
""",
        """    showLoader({
        kicker: "CATALOG · STAGE 1 / 2",
        title: "正在打开评测目录",
        message: "先读取轻量索引；题库只在你选择 Bench 后加载。",
    });
    setNavStatus("loading", "读取目录");
""",
        label="private catalog-loading branch",
    )
    app = replace_once(
        app,
        """    if (isIngestionLocation()) {
        dom.loadingLayer.classList.add("hidden");
        setNavStatus("error", "目录暂不可用 · 接入仍可使用");
        return;
    }
""",
        "",
        label="private catalog-error branch",
    )
    app = replace_once(
        app,
        """    dom.ingestionWorkspace.classList.add("hidden");
    globalThis.KwBenchIngestion?.deactivate();
""",
        "",
        label="private bench-selection state",
    )
    app = replace_once(
        app,
        (
            '            "浏览器不会携带 Hugging Face Token；Gold answer、答案哈希与 oracle 页码"\n'
            '                + "均未进入题库 shard、搜索索引或 Verifier 配置。",\n'
        ),
        (
            '            "本站不会代用户访问受门禁保护的数据；Gold answer、答案哈希"\n'
            '                + "与 oracle 页码均未进入题库 shard、搜索索引"\n'
            '                + "或 Verifier 配置。",\n'
        ),
        label="gated-data credential copy",
    )
    app = replace_once(
        app,
        "HF 授权内网镜像 · 问题可审阅，答案已排除",
        "授权数据 · 可公开问题可审阅，答案已排除",
        label="gated-data heading",
    )
    app = replace_once(
        app,
        """    dom.ingestionWorkspace.classList.add("hidden");
    dom.catalogHome.classList.remove("hidden");
    globalThis.KwBenchIngestion?.deactivate();
""",
        """    dom.catalogHome.classList.remove("hidden");
""",
        label="private catalog-home state",
    )
    app = replace_once(
        app,
        """    dom.ingestionWorkspace.classList.add("hidden");
""",
        "",
        label="private fatal-state workspace",
    )
    app = replace_once(
        app,
        """    const params = new URLSearchParams(location.hash.replace(/^#/, ""));
    if (!state.activeBenchId && params.get("view") !== "ingestion") {
""",
        """    if (!state.activeBenchId) {
""",
        label="private fatal-state location",
    )
    app = regex_replace_once(
        app,
        r"\nfunction showIngestionWorkspace\(options = \{\}\) \{.*?"
        r"\n\}\n\nfunction isIngestionLocation\(\) \{.*?\n\}\n"
        r"(?=\nfunction handleHashChange)",
        "",
        label="private workspace functions",
    )
    app = replace_once(
        app,
        """    const view = params.get("view") || "";
    if (view === "ingestion") {
        showIngestionWorkspace({
            jobId: params.get("job") || "",
            scroll: false,
            updateLocation: false,
        });
        return;
    }
""",
        "",
        label="private hash route",
    )
    app = regex_replace_once(
        app,
        r"\nfunction updateIngestionLocation\(jobId\) \{.*?\n\}\n"
        r"(?=\nfunction updateLocation)",
        "",
        label="private location writer",
    )

    public_copy = {
        "本地审计文件读取失败": "公开审计文件读取失败",
        "本地镜像覆盖": "站内镜像覆盖",
        "本地审计读取失败": "公开审计读取失败",
        "正在读取本地审计": "正在读取公开审计",
        "本地 / 可索引公开": "站内镜像 / 可索引公开",
        "等待本地镜像索引": "等待站内镜像索引",
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
        "本地镜像已就绪": "站内镜像已就绪",
    }
    for internal_text, public_text in public_copy.items():
        app = app.replace(internal_text, public_text)
    return app


def assert_public_output(index: str, app: str, styles: str, config: str) -> None:
    """Verify that no internal intake vocabulary reaches deployable assets."""
    surfaces = {
        "index.html": index,
        "app.js": app,
        "styles.css": styles,
        "public-config.js": config,
    }
    for filename, content in surfaces.items():
        blocked = find_blocked_public_text(content)
        if blocked:
            label, spelling = blocked
            raise ValueError(
                f"public {filename} contains blocked {label}: {spelling}"
            )

    if "KW_BENCH_PUBLIC_MODE = true" not in config:
        raise ValueError("public runtime flag is missing")
    config_offset = index.find("public-config.js")
    app_offset = index.find("app.js")
    if config_offset < 0 or app_offset < 0 or config_offset > app_offset:
        raise ValueError("public mode must be configured before app.js")
    if "noindex" in index or "nofollow" in index:
        raise ValueError("public page still opts out of indexing")


def parse_args() -> argparse.Namespace:
    """Parse source and output directory overrides from the command line."""
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
    """Build and validate all public UI assets into the output directory."""
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
    styles = build_styles((source_dir / "styles.css").read_text(encoding="utf-8"))
    config = config_path.read_text(encoding="utf-8")
    assert_public_output(index, app, styles, config)

    (output_dir / "index.html").write_text(index, encoding="utf-8")
    (output_dir / "app.js").write_text(app, encoding="utf-8")
    (output_dir / "styles.css").write_text(styles, encoding="utf-8")
    print(f"Built public UI in {output_dir}")


if __name__ == "__main__":
    main()
