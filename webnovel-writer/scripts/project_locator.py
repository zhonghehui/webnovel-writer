#!/usr/bin/env python3
"""
Project location helpers for webnovel-writer scripts.

This module only supports neutral naming conventions.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

from runtime_compat import normalize_windows_path


DEFAULT_PROJECT_DIR_NAMES: tuple[str, ...] = ("webnovel-project",)
CURRENT_PROJECT_POINTER_REL: Path = Path(".webnovel-current-project")
GLOBAL_REGISTRY_REL: Path = Path("webnovel-writer") / "workspaces.json"

ENV_WEBNOVEL_PROJECT_DIR = "WEBNOVEL_PROJECT_DIR"
ENV_WEBNOVEL_HOME = "WEBNOVEL_HOME"


def _find_git_root(cwd: Path) -> Optional[Path]:
    """Return nearest git root for cwd, if any."""
    for candidate in (cwd, *cwd.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _normcase_path_key(path: Path) -> str:
    """Build a stable map key (case-insensitive on Windows)."""
    try:
        resolved = path.expanduser().resolve()
    except Exception:
        resolved = path.expanduser()
    return os.path.normcase(str(resolved))


def _normalize_user_path(raw: str) -> Path:
    try:
        return normalize_windows_path(raw).expanduser().resolve()
    except Exception:
        return normalize_windows_path(raw).expanduser()


def _iter_user_home_roots() -> list[Path]:
    """
    Candidate user home roots for global registry/.env lookup.

    Precedence:
    1) WEBNOVEL_HOME
    2) ~/.webnovel
    """
    roots: list[Path] = []
    seen: set[str] = set()

    raw = os.environ.get(ENV_WEBNOVEL_HOME)
    if raw:
        root = _normalize_user_path(raw)
        key = _normcase_path_key(root)
        if key not in seen:
            seen.add(key)
            roots.append(root)

    default = Path.home() / ".webnovel"
    try:
        root = default.resolve()
    except Exception:
        root = default
    key = _normcase_path_key(root)
    if key not in seen:
        roots.append(root)

    return roots


def _global_registry_paths() -> list[Path]:
    return [root / GLOBAL_REGISTRY_REL for root in _iter_user_home_roots()]


def _global_registry_path() -> Path:
    paths = _global_registry_paths()
    if paths:
        return paths[0]
    # defensive fallback
    return (Path.home() / ".webnovel" / GLOBAL_REGISTRY_REL).resolve()


def _workspace_env_hint() -> Optional[Path]:
    raw = os.environ.get(ENV_WEBNOVEL_PROJECT_DIR)
    if not raw:
        return None
    try:
        return normalize_windows_path(raw).expanduser().resolve()
    except Exception:
        return normalize_windows_path(raw).expanduser()


def _default_registry() -> dict:
    return {
        "schema_version": 1,
        "workspaces": {},
        "last_used_project_root": "",
        "updated_at": _now_iso(),
    }


def _load_global_registry(path: Path) -> dict:
    if not path.is_file():
        return _default_registry()
    try:
        data = json.loads(path.read_text(encoding="utf-8") or "{}")
    except Exception:
        return _default_registry()
    if not isinstance(data, dict):
        return _default_registry()

    if data.get("schema_version") != 1:
        data["schema_version"] = 1
    if not isinstance(data.get("workspaces"), dict):
        data["workspaces"] = {}
    if not isinstance(data.get("last_used_project_root"), str):
        data["last_used_project_root"] = ""
    if not isinstance(data.get("updated_at"), str):
        data["updated_at"] = _now_iso()
    return data


def _save_global_registry(path: Path, data: dict) -> None:
    """Best-effort write; must not block the main flow."""
    try:
        from security_utils import atomic_write_json

        data["updated_at"] = _now_iso()
        atomic_write_json(path, data, backup=False)
    except Exception:
        return


def _resolve_project_root_from_global_registry(
    base: Path,
    *,
    workspace_hint: Optional[Path] = None,
    allow_last_used_fallback: bool = False,
) -> Optional[Path]:
    """
    Resolve project_root from user-level registry.

    Safety:
    - Prefer explicit workspace hints (env/arg/cwd).
    - Disable last_used fallback by default to avoid cross-workspace misbinding.
    """
    hints: list[Path] = []
    env_ws = _workspace_env_hint()
    if env_ws is not None:
        hints.append(env_ws)
    if workspace_hint is not None:
        hints.append(workspace_hint)
    hints.append(base)

    for reg_path in _global_registry_paths():
        reg = _load_global_registry(reg_path)
        workspaces = reg.get("workspaces") or {}
        if not isinstance(workspaces, dict) or not workspaces:
            continue

        # 1) Exact workspace key match.
        for hint in hints:
            key = _normcase_path_key(hint)
            entry = workspaces.get(key)
            if not isinstance(entry, dict):
                continue
            raw = entry.get("current_project_root")
            if not isinstance(raw, str) or not raw.strip():
                continue
            target = normalize_windows_path(raw).expanduser()
            if target.is_absolute() and _is_project_root(target):
                return target.resolve()

        # 2) Prefix match, useful when running from a workspace child directory.
        for hint in hints:
            hint_key = _normcase_path_key(hint)
            best_key: Optional[str] = None
            best_len = -1
            for ws_key in workspaces.keys():
                if not isinstance(ws_key, str) or not ws_key:
                    continue
                ws_key_norm = os.path.normcase(ws_key)
                if hint_key == ws_key_norm or hint_key.startswith(ws_key_norm.rstrip("\\") + "\\"):
                    if len(ws_key_norm) > best_len:
                        best_key = ws_key
                        best_len = len(ws_key_norm)
            if not best_key:
                continue
            entry = workspaces.get(best_key)
            if not isinstance(entry, dict):
                continue
            raw = entry.get("current_project_root")
            if not isinstance(raw, str) or not raw.strip():
                continue
            target = normalize_windows_path(raw).expanduser()
            if target.is_absolute() and _is_project_root(target):
                return target.resolve()

        # 3) Optional last_used fallback.
        if allow_last_used_fallback:
            raw = reg.get("last_used_project_root")
            if isinstance(raw, str) and raw.strip():
                target = normalize_windows_path(raw).expanduser()
                if target.is_absolute() and _is_project_root(target):
                    return target.resolve()

    return None


def update_global_registry_current_project(
    *,
    workspace_root: Optional[Path],
    project_root: Path,
) -> Optional[Path]:
    """
    Update user-level registry mapping: workspace_root -> current_project_root.

    Returns written registry path, or None when workspace root is unavailable.
    """
    root = normalize_windows_path(project_root).expanduser()
    try:
        root = root.resolve()
    except Exception:
        pass
    if not _is_project_root(root):
        raise FileNotFoundError(f"Not a webnovel project root (missing .webnovel/state.json): {root}")

    ws = workspace_root
    if ws is None:
        ws = _workspace_env_hint()
    if ws is None:
        return None

    try:
        ws = normalize_windows_path(ws).expanduser().resolve()
    except Exception:
        ws = normalize_windows_path(ws).expanduser()

    reg_path = _global_registry_path()
    reg = _load_global_registry(reg_path)
    workspaces = reg.get("workspaces")
    if not isinstance(workspaces, dict):
        workspaces = {}
        reg["workspaces"] = workspaces

    workspaces[_normcase_path_key(ws)] = {
        "workspace_root": str(ws),
        "current_project_root": str(root),
        "updated_at": _now_iso(),
    }
    reg["last_used_project_root"] = str(root)
    _save_global_registry(reg_path, reg)
    return reg_path


def _candidate_roots(cwd: Path, *, stop_at: Optional[Path] = None) -> Iterable[Path]:
    yield cwd
    for name in DEFAULT_PROJECT_DIR_NAMES:
        yield cwd / name

    for parent in cwd.parents:
        yield parent
        for name in DEFAULT_PROJECT_DIR_NAMES:
            yield parent / name
        if stop_at is not None and parent == stop_at:
            break


def _is_project_root(path: Path) -> bool:
    return (path / ".webnovel" / "state.json").is_file()


def _pointer_candidates(cwd: Path, *, stop_at: Optional[Path] = None) -> Iterable[Path]:
    """Yield pointer candidates from cwd up to parents."""
    for candidate in (cwd, *cwd.parents):
        yield candidate / CURRENT_PROJECT_POINTER_REL
        if stop_at is not None and candidate == stop_at:
            break


def _resolve_project_root_from_pointer(cwd: Path, *, stop_at: Optional[Path] = None) -> Optional[Path]:
    """
    Resolve project root from workspace pointer files.

    Pointer format: plain text path (absolute or relative, relative to workspace root).
    """
    for pointer_file in _pointer_candidates(cwd, stop_at=stop_at):
        if not pointer_file.is_file():
            continue
        try:
            raw = pointer_file.read_text(encoding="utf-8").strip()
        except Exception:
            continue
        if not raw:
            continue
        target = normalize_windows_path(raw).expanduser()
        if not target.is_absolute():
            target = (pointer_file.parent / target).resolve()
        if _is_project_root(target):
            return target.resolve()
    return None


def _find_workspace_root_with_markers(start: Path) -> Optional[Path]:
    """Find nearest ancestor containing `.webnovel-current-project`."""
    for candidate in (start, *start.parents):
        if (candidate / CURRENT_PROJECT_POINTER_REL).exists():
            return candidate
    return None


def _write_pointer_file(pointer_file: Path, target_root: Path) -> Optional[Path]:
    try:
        pointer_file.write_text(str(target_root), encoding="utf-8")
        return pointer_file
    except Exception:
        return None


def write_current_project_pointer(project_root: Path, *, workspace_root: Optional[Path] = None) -> Optional[Path]:
    """
    Write workspace-level pointer and return pointer path.

    If workspace root cannot be inferred, fallback to project parent only for registry update.
    """
    root = normalize_windows_path(project_root).expanduser().resolve()
    if not _is_project_root(root):
        raise FileNotFoundError(f"Not a webnovel project root (missing .webnovel/state.json): {root}")

    ws_root: Optional[Path]
    if workspace_root is not None:
        ws_root = normalize_windows_path(workspace_root).expanduser()
        try:
            ws_root = ws_root.resolve()
        except Exception:
            pass
    else:
        ws_root = _workspace_env_hint()
        if ws_root is None:
            ws_root = _find_workspace_root_with_markers(root)
        if ws_root is None:
            ws_root = _find_workspace_root_with_markers(Path.cwd().resolve())

    if ws_root is None:
        ws_root = root.parent if root.parent != root else None

    pointer_file: Optional[Path] = None
    if ws_root is not None:
        pointer_file = _write_pointer_file(ws_root / CURRENT_PROJECT_POINTER_REL, root)

    # Best-effort registry update (non-blocking)
    try:
        update_global_registry_current_project(workspace_root=ws_root, project_root=root)
    except Exception:
        pass

    return pointer_file


def resolve_project_root(explicit_project_root: Optional[str] = None, *, cwd: Optional[Path] = None) -> Path:
    """
    Resolve the webnovel project root (directory containing `.webnovel/state.json`).

    Resolution order:
    1) explicit_project_root (book root or workspace root)
    2) env WEBNOVEL_PROJECT_ROOT
    3) pointer fallback from cwd
    4) user-level registry fallback
    5) filesystem search from cwd upward, including `webnovel-project/`
    """
    if explicit_project_root:
        root = normalize_windows_path(explicit_project_root).expanduser().resolve()
        if _is_project_root(root):
            return root

        pointer_root = _resolve_project_root_from_pointer(root, stop_at=_find_git_root(root))
        if pointer_root is not None:
            return pointer_root

        reg_root = _resolve_project_root_from_global_registry(
            root,
            workspace_hint=root,
            allow_last_used_fallback=False,
        )
        if reg_root is not None:
            return reg_root

        # Explicit path is trusted for CLI flows that may bootstrap `.webnovel` later.
        if root.is_dir():
            return root

        raise FileNotFoundError(f"Not a webnovel project root (missing .webnovel/state.json): {root}")

    env_root = os.environ.get("WEBNOVEL_PROJECT_ROOT")
    if env_root:
        root = normalize_windows_path(env_root).expanduser().resolve()
        if _is_project_root(root):
            return root
        raise FileNotFoundError(f"WEBNOVEL_PROJECT_ROOT is set but invalid (missing .webnovel/state.json): {root}")

    base = (cwd or Path.cwd()).resolve()
    git_root = _find_git_root(base)

    pointer_root = _resolve_project_root_from_pointer(base, stop_at=git_root)
    if pointer_root is not None:
        return pointer_root

    allow_last_used = _workspace_env_hint() is not None
    reg_root = _resolve_project_root_from_global_registry(
        base,
        workspace_hint=None,
        allow_last_used_fallback=allow_last_used,
    )
    if reg_root is not None:
        return reg_root

    for candidate in _candidate_roots(base, stop_at=git_root):
        if _is_project_root(candidate):
            return candidate.resolve()

    raise FileNotFoundError(
        "Unable to locate webnovel project root. Expected `.webnovel/state.json` under the current directory, "
        "a parent directory, or `webnovel-project/`. Run /webnovel-init first or pass --project-root / set "
        "WEBNOVEL_PROJECT_ROOT."
    )


def resolve_state_file(
    explicit_state_file: Optional[str] = None,
    *,
    explicit_project_root: Optional[str] = None,
    cwd: Optional[Path] = None,
) -> Path:
    """
    Resolve `.webnovel/state.json` path.

    If explicit_state_file is provided, returns it as-is (resolved to absolute if relative).
    Otherwise derives it from resolve_project_root().
    """
    base = (cwd or Path.cwd()).resolve()
    if explicit_state_file:
        path = Path(explicit_state_file).expanduser()
        return (base / path).resolve() if not path.is_absolute() else path.resolve()

    root = resolve_project_root(explicit_project_root, cwd=base)
    return root / ".webnovel" / "state.json"
