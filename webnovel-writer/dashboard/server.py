"""
Dashboard launcher.

Usage:
    python -m dashboard.server --project-root /path/to/novel-project
    python -m dashboard.server  # auto-resolve from env/pointer/cwd
"""

from __future__ import annotations

import argparse
import os
import sys
import webbrowser
from pathlib import Path

from scripts.project_locator import resolve_project_root


def _resolve_project_root(cli_root: str | None) -> Path:
    """Resolve PROJECT_ROOT: CLI > env/pointer/cwd via shared locator."""
    try:
        if cli_root:
            return resolve_project_root(cli_root, cwd=Path.cwd())
        return resolve_project_root(cwd=Path.cwd())
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Webnovel Dashboard Server")
    parser.add_argument("--project-root", type=str, default=None, help="小说项目根目录")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址")
    parser.add_argument("--port", type=int, default=8765, help="监听端口")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    args = parser.parse_args()

    project_root = _resolve_project_root(args.project_root)
    os.environ["WEBNOVEL_PROJECT_ROOT"] = str(project_root)
    print(f"项目路径: {project_root}")

    import uvicorn
    from .app import create_app

    app = create_app(project_root)

    url = f"http://{args.host}:{args.port}"
    print(f"Dashboard 启动: {url}")
    print(f"API 文档: {url}/docs")

    if not args.no_browser:
        webbrowser.open(url)

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
