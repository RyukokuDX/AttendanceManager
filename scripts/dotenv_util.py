"""Walk upward from a directory and load the first `.env` found (no override of os.environ)."""
from __future__ import annotations

import os
from pathlib import Path


def load_repo_dotenv(start_dir: Path) -> None:
    d = start_dir.resolve()
    if d.is_file():
        d = d.parent
    for cur in [d, *d.parents]:
        path = cur / ".env"
        if path.is_file():
            _parse_env_file(path)
            return


def _parse_env_file(path: Path) -> None:
    for enc in ("utf-8-sig", "utf-8", "cp932"):
        try:
            text = path.read_text(encoding=enc)
            break
        except OSError:
            return
        except UnicodeDecodeError:
            continue
    else:
        return
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if "=" not in s:
            continue
        key, _, val = s.partition("=")
        key = key.strip()
        if not key:
            continue
        val = val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        if key not in os.environ:
            os.environ[key] = val
