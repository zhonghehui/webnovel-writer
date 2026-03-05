#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from pathlib import Path


def _ensure_scripts_on_path() -> None:
    scripts_dir = Path(__file__).resolve().parents[2]
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))


def _create_project_root(root: Path) -> None:
    (root / ".webnovel").mkdir(parents=True, exist_ok=True)
    (root / ".webnovel" / "state.json").write_text("{}", encoding="utf-8")


def test_resolve_project_root_prefers_cwd_project(tmp_path):
    _ensure_scripts_on_path()
    from project_locator import resolve_project_root

    project_root = tmp_path / "workspace"
    _create_project_root(project_root)

    resolved = resolve_project_root(cwd=project_root)
    assert resolved == project_root.resolve()


def test_resolve_project_root_stops_at_git_root(tmp_path):
    _ensure_scripts_on_path()
    from project_locator import resolve_project_root

    repo_root = tmp_path / "repo"
    (repo_root / ".git").mkdir(parents=True, exist_ok=True)

    nested = repo_root / "sub" / "dir"
    nested.mkdir(parents=True, exist_ok=True)

    outside_project = tmp_path / "outside_project"
    _create_project_root(outside_project)

    try:
        resolve_project_root(cwd=nested)
        assert False, "Expected FileNotFoundError when only parent outside git root has project"
    except FileNotFoundError:
        pass


def test_resolve_project_root_finds_default_subdir_within_git_root(tmp_path):
    _ensure_scripts_on_path()
    from project_locator import resolve_project_root

    repo_root = tmp_path / "repo"
    (repo_root / ".git").mkdir(parents=True, exist_ok=True)

    default_project = repo_root / "webnovel-project"
    _create_project_root(default_project)

    nested = repo_root / "sub" / "dir"
    nested.mkdir(parents=True, exist_ok=True)

    resolved = resolve_project_root(cwd=nested)
    assert resolved == default_project.resolve()


def test_write_pointer_writes_neutral_pointer_without_legacy_dir(tmp_path):
    _ensure_scripts_on_path()
    from project_locator import (
        CURRENT_PROJECT_POINTER_REL,
        LEGACY_PROJECT_POINTER_REL,
        resolve_project_root,
        write_current_project_pointer,
    )

    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    project_root = workspace / "book"
    _create_project_root(project_root)

    pointer_file = write_current_project_pointer(project_root, workspace_root=workspace)
    assert pointer_file == (workspace / CURRENT_PROJECT_POINTER_REL)
    assert pointer_file.is_file()
    assert not (workspace / LEGACY_PROJECT_POINTER_REL).exists()

    resolved = resolve_project_root(cwd=workspace)
    assert resolved == project_root.resolve()


def test_write_pointer_mirrors_legacy_when_claude_dir_exists(tmp_path):
    _ensure_scripts_on_path()
    from project_locator import (
        CURRENT_PROJECT_POINTER_REL,
        LEGACY_PROJECT_POINTER_REL,
        write_current_project_pointer,
    )

    workspace = tmp_path / "workspace"
    (workspace / ".claude").mkdir(parents=True, exist_ok=True)
    project_root = workspace / "book"
    _create_project_root(project_root)

    pointer_file = write_current_project_pointer(project_root, workspace_root=workspace)
    assert pointer_file == (workspace / CURRENT_PROJECT_POINTER_REL)
    assert (workspace / CURRENT_PROJECT_POINTER_REL).is_file()
    assert (workspace / LEGACY_PROJECT_POINTER_REL).is_file()


def test_resolve_project_root_supports_legacy_pointer(tmp_path):
    _ensure_scripts_on_path()
    from project_locator import resolve_project_root

    workspace = tmp_path / "workspace"
    (workspace / ".claude").mkdir(parents=True, exist_ok=True)
    project_root = workspace / "book"
    _create_project_root(project_root)

    (workspace / ".claude" / ".webnovel-current-project").write_text(str(project_root), encoding="utf-8")

    resolved = resolve_project_root(cwd=workspace)
    assert resolved == project_root.resolve()


def test_resolve_project_root_ignores_stale_pointer_and_fallbacks(tmp_path):
    _ensure_scripts_on_path()
    from project_locator import resolve_project_root

    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / ".webnovel-current-project").write_text(str(workspace / "missing-project"), encoding="utf-8")

    default_project = workspace / "webnovel-project"
    _create_project_root(default_project)

    resolved = resolve_project_root(cwd=workspace)
    assert resolved == default_project.resolve()
