#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified CLI entry for webnovel tooling.
"""

from __future__ import annotations

import argparse
import importlib
import subprocess
import sys
from pathlib import Path
from typing import Optional

from runtime_compat import normalize_windows_path
from project_locator import (
    resolve_project_root,
    update_global_registry_current_project,
    write_current_project_pointer,
)


def _scripts_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def _resolve_root(explicit_project_root: Optional[str]) -> Path:
    return resolve_project_root(explicit_project_root) if explicit_project_root else resolve_project_root()


def _strip_project_root_args(argv: list[str]) -> list[str]:
    out: list[str] = []
    i = 0
    while i < len(argv):
        tok = argv[i]
        if tok == "--project-root":
            i += 2
            continue
        if tok.startswith("--project-root="):
            i += 1
            continue
        out.append(tok)
        i += 1
    return out


def _run_data_module(module: str, argv: list[str]) -> int:
    mod = importlib.import_module(f"data_modules.{module}")
    main = getattr(mod, "main", None)
    if not callable(main):
        raise RuntimeError(f"data_modules.{module} missing callable main()")

    old_argv = sys.argv
    try:
        sys.argv = [f"data_modules.{module}"] + argv
        try:
            main()
            return 0
        except SystemExit as exc:
            return int(exc.code or 0)
    finally:
        sys.argv = old_argv


def _run_script(script_name: str, argv: list[str]) -> int:
    script_path = _scripts_dir() / script_name
    if not script_path.is_file():
        raise FileNotFoundError(f"Script not found: {script_path}")
    proc = subprocess.run([sys.executable, str(script_path), *argv])
    return int(proc.returncode or 0)


def cmd_where(args: argparse.Namespace) -> int:
    print(str(_resolve_root(args.project_root)))
    return 0


def cmd_use(args: argparse.Namespace) -> int:
    project_root = normalize_windows_path(args.project_root).expanduser()
    try:
        project_root = project_root.resolve()
    except Exception:
        pass

    workspace_root: Optional[Path] = None
    if args.workspace_root:
        workspace_root = normalize_windows_path(args.workspace_root).expanduser()
        try:
            workspace_root = workspace_root.resolve()
        except Exception:
            pass

    pointer_file = write_current_project_pointer(project_root, workspace_root=workspace_root)
    print(f"workspace pointer: {pointer_file}" if pointer_file is not None else "workspace pointer: (skipped)")

    reg_path = update_global_registry_current_project(workspace_root=workspace_root, project_root=project_root)
    print(f"global registry: {reg_path}" if reg_path is not None else "global registry: (skipped)")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="webnovel unified CLI")
    parser.add_argument("--project-root", help="book root or workspace root")

    sub = parser.add_subparsers(dest="tool", required=True)

    p_where = sub.add_parser("where", help="print resolved project root")
    p_where.set_defaults(func=cmd_where)

    p_use = sub.add_parser("use", help="bind workspace to current book project")
    p_use.add_argument("project_root", help="book project root")
    p_use.add_argument("--workspace-root", help="workspace root (optional)")
    p_use.set_defaults(func=cmd_use)

    # Pass-through to data modules
    for name in ("index", "state", "rag", "style", "entity", "context", "migrate"):
        p = sub.add_parser(name)
        p.add_argument("args", nargs=argparse.REMAINDER)

    # Pass-through to scripts
    for name in ("workflow", "status", "update-state", "backup", "archive", "init"):
        p = sub.add_parser(name)
        p.add_argument("args", nargs=argparse.REMAINDER)

    p_extract = sub.add_parser("extract-context")
    p_extract.add_argument("--chapter", type=int, required=True)
    p_extract.add_argument("--format", choices=["text", "json"], default="text")
    return parser


def main() -> None:
    from .cli_args import normalize_global_project_root

    parser = _build_parser()
    argv = normalize_global_project_root(sys.argv[1:])
    args = parser.parse_args(argv)

    if hasattr(args, "func"):
        raise SystemExit(int(args.func(args) or 0))

    tool = str(args.tool)
    rest = list(getattr(args, "args", []) or [])
    if rest[:1] == ["--"]:
        rest = rest[1:]
    rest = _strip_project_root_args(rest)

    if tool == "init":
        raise SystemExit(_run_script("init_project.py", rest))

    project_root = _resolve_root(args.project_root)
    forward_args = ["--project-root", str(project_root), *rest]

    data_module_map = {
        "index": "index_manager",
        "state": "state_manager",
        "rag": "rag_adapter",
        "style": "style_sampler",
        "entity": "entity_linker",
        "context": "context_manager",
        "migrate": "migrate_state_to_sqlite",
    }
    if tool in data_module_map:
        raise SystemExit(_run_data_module(data_module_map[tool], forward_args))

    script_map = {
        "workflow": "workflow_manager.py",
        "status": "status_reporter.py",
        "update-state": "update_state.py",
        "backup": "backup_manager.py",
        "archive": "archive_manager.py",
    }
    if tool in script_map:
        raise SystemExit(_run_script(script_map[tool], forward_args))

    if tool == "extract-context":
        extract_args = [
            "--project-root",
            str(project_root),
            "--chapter",
            str(args.chapter),
            "--format",
            str(args.format),
        ]
        raise SystemExit(_run_script("extract_chapter_context.py", extract_args))

    raise SystemExit(2)


if __name__ == "__main__":
    main()
