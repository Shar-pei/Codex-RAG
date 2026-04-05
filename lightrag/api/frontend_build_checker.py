from __future__ import annotations

from pathlib import Path

from ascii_colors import ASCIIColors

from lightrag.utils import logger


def check_frontend_build(base_api_dir: Path | None = None) -> tuple[bool, bool]:
    """Check if frontend is built and whether local source is newer than the build."""
    if base_api_dir is None:
        base_api_dir = Path(__file__).parent

    webui_dir = base_api_dir / "webui"
    index_html = webui_dir / "index.html"

    if not index_html.exists():
        ASCIIColors.yellow("\n" + "=" * 80)
        ASCIIColors.yellow("WARNING: Frontend Not Built")
        ASCIIColors.yellow("=" * 80)
        ASCIIColors.yellow("The WebUI frontend has not been built yet.")
        ASCIIColors.yellow("The API server will start without the WebUI interface.")
        ASCIIColors.yellow(
            "\nTo enable WebUI, build the frontend using these commands:\n"
        )
        ASCIIColors.cyan("    cd lightrag_webui")
        ASCIIColors.cyan("    bun install --frozen-lockfile")
        ASCIIColors.cyan("    bun run build")
        ASCIIColors.cyan("    cd ..")
        ASCIIColors.yellow("\nThen restart the service.\n")
        ASCIIColors.cyan(
            "Note: Make sure you have Bun installed. Visit https://bun.sh for installation."
        )
        ASCIIColors.yellow("=" * 80 + "\n")
        return (False, False)

    try:
        source_dir = base_api_dir.parent.parent / "lightrag_webui"
        src_dir = source_dir / "src"

        if not source_dir.exists() or not src_dir.exists():
            logger.debug(
                "Production environment detected, skipping source freshness check"
            )
            return (True, False)

        logger.debug("Development environment detected, checking source freshness")

        source_extensions = {
            ".ts",
            ".tsx",
            ".js",
            ".jsx",
            ".mjs",
            ".cjs",
            ".css",
            ".scss",
            ".sass",
            ".less",
            ".json",
            ".jsonc",
            ".html",
            ".htm",
            ".md",
            ".mdx",
        }
        key_files = [
            source_dir / "package.json",
            source_dir / "bun.lock",
            source_dir / "vite.config.ts",
            source_dir / "tsconfig.json",
            source_dir / "tailraid.config.js",
            source_dir / "index.html",
        ]

        latest_source_time = 0.0
        for file_path in src_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in source_extensions:
                latest_source_time = max(latest_source_time, file_path.stat().st_mtime)

        for key_file in key_files:
            if key_file.exists():
                latest_source_time = max(latest_source_time, key_file.stat().st_mtime)

        build_time = index_html.stat().st_mtime

        if latest_source_time > build_time + 5:
            ASCIIColors.yellow("\n" + "=" * 80)
            ASCIIColors.yellow("WARNING: Frontend Source Code Has Been Updated")
            ASCIIColors.yellow("=" * 80)
            ASCIIColors.yellow(
                "The frontend source code is newer than the current build."
            )
            ASCIIColors.yellow(
                "This might happen after 'git pull' or manual code changes.\n"
            )
            ASCIIColors.cyan(
                "Recommended: Rebuild the frontend to use the latest changes:"
            )
            ASCIIColors.cyan("    cd lightrag_webui")
            ASCIIColors.cyan("    bun install --frozen-lockfile")
            ASCIIColors.cyan("    bun run build")
            ASCIIColors.cyan("    cd ..")
            ASCIIColors.yellow("\nThe server will continue with the current build.")
            ASCIIColors.yellow("=" * 80 + "\n")
            return (True, True)

        logger.info("Frontend build is up-to-date")
        return (True, False)

    except Exception as exc:
        logger.warning(f"Failed to check frontend source freshness: {exc}")
        return (True, False)
