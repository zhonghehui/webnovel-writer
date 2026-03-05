#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
webnovel unified launcher (no mandatory `cd`).

Examples:
  python "<SCRIPTS_DIR>/webnovel.py" where
  python "<SCRIPTS_DIR>/webnovel.py" index stats

This wrapper only ensures `scripts/` is on sys.path, then forwards
to `data_modules.webnovel`.
"""

from __future__ import annotations

import sys
from pathlib import Path

from runtime_compat import enable_windows_utf8_stdio


def main() -> None:
    scripts_dir = Path(__file__).resolve().parent
    sys.path.insert(0, str(scripts_dir))

    # Lazy import after sys.path patch.
    from data_modules.webnovel import main as _main

    _main()


if __name__ == "__main__":
    enable_windows_utf8_stdio(skip_in_pytest=True)
    main()
