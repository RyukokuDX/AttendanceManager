#!/usr/bin/env python3
"""Delete students whose name contains any of the given surnames (substring match)."""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


def _bootstrap_dotenv_util() -> None:
    here = Path(__file__).resolve()
    for p in here.parents:
        util = p / "scripts" / "dotenv_util.py"
        if util.is_file():
            sys.path.insert(0, str(p / "scripts"))
            return


_bootstrap_dotenv_util()
from dotenv_util import load_repo_dotenv  # noqa: E402


def main() -> int:
    load_repo_dotenv(Path(__file__).resolve().parent)
    default_base = os.environ.get("ATTEND_SERVER", "http://localhost:8889").rstrip("/")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base",
        default=default_base,
        help="API base URL. Default: .env ATTEND_SERVER or http://localhost:8889",
    )
    parser.add_argument(
        "surnames",
        nargs="+",
        help="Surnames to match as substrings in student name (e.g. 奥野 松本)",
    )
    args = parser.parse_args()
    base = args.base.rstrip("/")

    req = urllib.request.Request(
        f"{base}/api/students/",
        headers={"Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            students: list[dict] = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        print(f"ERROR: cannot reach API: {e}", file=sys.stderr)
        return 2

    targets = []
    for s in students:
        name = s.get("name") or ""
        for sur in args.surnames:
            if sur in name:
                targets.append((s["student_id"], name, sur))
                break

    if not targets:
        print("No matching students.")
        return 1

    for student_id, name, matched in targets:
        del_req = urllib.request.Request(
            f"{base}/api/students/{urllib.parse.quote(student_id, safe='')}",
            method="DELETE",
        )
        try:
            with urllib.request.urlopen(del_req, timeout=30) as resp:
                body = resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            print(f"FAIL {student_id} {name} ({matched}): HTTP {e.code} {e.read().decode()}")
            continue
        print(f"OK {student_id} {name} (matched: {matched}) -> {body}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
