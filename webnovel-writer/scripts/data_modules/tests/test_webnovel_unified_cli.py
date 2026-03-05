#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import types
from argparse import Namespace
from pathlib import Path

import pytest


def _ensure_scripts_on_path() -> None:
    scripts_dir = Path(__file__).resolve().parents[2]
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))


def _load_webnovel_module():
    _ensure_scripts_on_path()
    import data_modules.webnovel as webnovel_module

    return webnovel_module


def test_init_does_not_resolve_existing_project_root(monkeypatch):
    module = _load_webnovel_module()

    called = {}

    def _fake_run_script(script_name, argv):
        called["script_name"] = script_name
        called["argv"] = list(argv)
        return 0

    def _fail_resolve(_explicit_project_root=None):
        raise AssertionError("init 子命令不应触发 project_root 解析")

    monkeypatch.setenv("WEBNOVEL_PROJECT_ROOT", r"D:\invalid\root")
    monkeypatch.setattr(module, "_run_script", _fake_run_script)
    monkeypatch.setattr(module, "_resolve_root", _fail_resolve)
    monkeypatch.setattr(sys, "argv", ["webnovel", "init", "proj-dir", "测试书", "修仙"])

    with pytest.raises(SystemExit) as exc:
        module.main()

    assert int(exc.value.code or 0) == 0
    assert called["script_name"] == "init_project.py"
    assert called["argv"] == ["proj-dir", "测试书", "修仙"]


def test_extract_context_forwards_with_resolved_project_root(monkeypatch, tmp_path):
    module = _load_webnovel_module()

    book_root = (tmp_path / "book").resolve()
    called = {}

    def _fake_resolve(explicit_project_root=None):
        return book_root

    def _fake_run_script(script_name, argv):
        called["script_name"] = script_name
        called["argv"] = list(argv)
        return 0

    monkeypatch.setattr(module, "_resolve_root", _fake_resolve)
    monkeypatch.setattr(module, "_run_script", _fake_run_script)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "webnovel",
            "--project-root",
            str(tmp_path),
            "extract-context",
            "--chapter",
            "12",
            "--format",
            "json",
        ],
    )

    with pytest.raises(SystemExit) as exc:
        module.main()

    assert int(exc.value.code or 0) == 0
    assert called["script_name"] == "extract_chapter_context.py"
    assert called["argv"] == [
        "--project-root",
        str(book_root),
        "--chapter",
        "12",
        "--format",
        "json",
    ]


def test_quality_trend_report_writes_to_book_root_when_input_is_workspace_root(tmp_path, monkeypatch):
    _ensure_scripts_on_path()
    import quality_trend_report as quality_trend_report_module

    workspace_root = (tmp_path / "workspace").resolve()
    book_root = (workspace_root / "凡人资本论").resolve()

    workspace_root.mkdir(parents=True, exist_ok=True)
    (workspace_root / ".webnovel-current-project").write_text(str(book_root), encoding="utf-8")

    (book_root / ".webnovel").mkdir(parents=True, exist_ok=True)
    (book_root / ".webnovel" / "state.json").write_text("{}", encoding="utf-8")

    output_path = workspace_root / "report.md"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "quality_trend_report",
            "--project-root",
            str(workspace_root),
            "--limit",
            "1",
            "--output",
            str(output_path),
        ],
    )

    quality_trend_report_module.main()

    assert output_path.is_file()
    assert (book_root / ".webnovel" / "index.db").is_file()
    assert not (workspace_root / ".webnovel" / "index.db").exists()


def test_strip_project_root_args_handles_both_forms():
    module = _load_webnovel_module()
    argv = [
        "index",
        "--project-root",
        "D:\\book",
        "stats",
        "--project-root=D:\\book2",
        "--foo",
    ]
    assert module._strip_project_root_args(argv) == ["index", "stats", "--foo"]


def test_run_data_module_returns_system_exit_and_restores_argv(monkeypatch):
    module = _load_webnovel_module()

    def _main():
        raise SystemExit(7)

    dummy_mod = types.SimpleNamespace(main=_main)
    monkeypatch.setattr(module.importlib, "import_module", lambda _name: dummy_mod)

    old_argv = list(sys.argv)
    code = module._run_data_module("dummy", ["--x"])
    assert code == 7
    assert sys.argv == old_argv


def test_run_data_module_returns_zero_when_main_succeeds(monkeypatch):
    module = _load_webnovel_module()
    called = {}

    def _main():
        called["ok"] = True

    dummy_mod = types.SimpleNamespace(main=_main)
    monkeypatch.setattr(module.importlib, "import_module", lambda _name: dummy_mod)

    code = module._run_data_module("dummy", ["--ok"])
    assert code == 0
    assert called.get("ok") is True


def test_run_data_module_raises_when_main_missing(monkeypatch):
    module = _load_webnovel_module()
    dummy_mod = types.SimpleNamespace(main=None)
    monkeypatch.setattr(module.importlib, "import_module", lambda _name: dummy_mod)

    with pytest.raises(RuntimeError):
        module._run_data_module("dummy", [])


def test_run_script_raises_when_script_missing(tmp_path, monkeypatch):
    module = _load_webnovel_module()
    monkeypatch.setattr(module, "_scripts_dir", lambda: tmp_path)

    with pytest.raises(FileNotFoundError):
        module._run_script("missing.py", [])


def test_run_script_returns_subprocess_code(tmp_path, monkeypatch):
    module = _load_webnovel_module()
    script = tmp_path / "ok.py"
    script.write_text("print('ok')", encoding="utf-8")

    monkeypatch.setattr(module, "_scripts_dir", lambda: tmp_path)
    monkeypatch.setattr(module.subprocess, "run", lambda _argv: types.SimpleNamespace(returncode=5))

    assert module._run_script("ok.py", ["--x"]) == 5


def test_cmd_where_prints_resolved_root(monkeypatch, capsys, tmp_path):
    module = _load_webnovel_module()
    monkeypatch.setattr(module, "_resolve_root", lambda _explicit=None: tmp_path)

    code = module.cmd_where(Namespace(project_root=str(tmp_path)))
    out = capsys.readouterr().out
    assert code == 0
    assert str(tmp_path) in out


def test_cmd_use_prints_skipped_when_pointer_and_registry_unavailable(tmp_path, monkeypatch, capsys):
    module = _load_webnovel_module()
    project_root = tmp_path / "book"
    project_root.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(module, "write_current_project_pointer", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(module, "update_global_registry_current_project", lambda *_args, **_kwargs: None)

    code = module.cmd_use(Namespace(project_root=str(project_root), workspace_root=None))
    out = capsys.readouterr().out
    assert code == 0
    assert "workspace pointer: (skipped)" in out
    assert "global registry: (skipped)" in out


def test_main_routes_data_module_branch(monkeypatch, tmp_path):
    module = _load_webnovel_module()
    called = {}

    monkeypatch.setattr(module, "_resolve_root", lambda _explicit=None: tmp_path)

    def _fake_run_data_module(name, argv):
        called["name"] = name
        called["argv"] = list(argv)
        return 0

    monkeypatch.setattr(module, "_run_data_module", _fake_run_data_module)
    monkeypatch.setattr(sys, "argv", ["webnovel", "index", "stats"])

    with pytest.raises(SystemExit) as exc:
        module.main()

    assert int(exc.value.code or 0) == 0
    assert called["name"] == "index_manager"
    assert called["argv"][:2] == ["--project-root", str(tmp_path)]


def test_main_routes_func_branch(monkeypatch):
    module = _load_webnovel_module()
    monkeypatch.setattr(sys, "argv", ["webnovel", "where"])
    monkeypatch.setattr(module, "cmd_where", lambda _args: 0)

    with pytest.raises(SystemExit) as exc:
        module.main()

    assert int(exc.value.code or 0) == 0


def test_main_routes_script_branch(monkeypatch, tmp_path):
    module = _load_webnovel_module()
    called = {}

    monkeypatch.setattr(module, "_resolve_root", lambda _explicit=None: tmp_path)

    def _fake_run_script(name, argv):
        called["name"] = name
        called["argv"] = list(argv)
        return 0

    monkeypatch.setattr(module, "_run_script", _fake_run_script)
    monkeypatch.setattr(sys, "argv", ["webnovel", "status", "--", "--focus", "all"])

    with pytest.raises(SystemExit) as exc:
        module.main()

    assert int(exc.value.code or 0) == 0
    assert called["name"] == "status_reporter.py"
    assert called["argv"][:2] == ["--project-root", str(tmp_path)]
