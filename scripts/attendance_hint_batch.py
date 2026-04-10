#!/usr/bin/env python3
"""
提示された学籍番号で API 操作を一括実行する。

1) 学生削除（出席・入室・Alert 含む。違反履歴も消える）
2) コアタイム POST（以前の指定どおり）

使い方:
  リポジトリ直下の .env に ATTEND_SERVER を書き、
  python scripts/attendance_hint_batch.py
  # 上書きのみ: --base "http://other:8889"
  # 既にシェルに ATTEND_SERVER がある場合は .env より優先（上書きしない）
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from dotenv_util import load_repo_dotenv

# 削除対象（奥野・松本・石原・森川・藤井）
DELETE_STUDENT_IDS = [
    "y24m001",
    "y220058",
    "y220065",
    "y200091",
    "y220083",
]

# コアタイム: student_id -> (ct1_day, ct1_period, ct2_day, ct2_period)  曜日1=月…7=日
CORETIME_BY_STUDENT: dict[str, tuple[int, int, int, int]] = {
    "y230033": (1, 3, 2, 3),  # 西谷 隆之: 月3 火3
    "y230028": (2, 2, 3, 3),  # 丸野 新士: 火2 水3
    "y230068": (1, 2, 4, 3),  # 石嶺 杏佳: 月2 木3
    "t190054": (3, 1, 3, 2),  # 鈴木 温也: 水1 水2
    "y230049": (1, 2, 2, 4),  # 冨元 蒼太: 月2 火4
    "y220020": (1, 2, 1, 3),  # 高木 勇輔: 月2 月3
}


def http_json(method: str, url: str, body: dict | None = None, timeout: float = 60.0):
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            if not raw:
                return resp.status, None
            return resp.status, json.loads(raw)
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        try:
            detail = json.loads(err_body)
        except json.JSONDecodeError:
            detail = err_body
        return e.code, detail


def main() -> int:
    load_repo_dotenv(Path(__file__).resolve().parent)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base",
        default=os.environ.get("ATTEND_SERVER", "").rstrip("/"),
        help="API ベース URL。省略時は .env または環境変数 ATTEND_SERVER",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="リクエストを送らず内容だけ表示",
    )
    args = parser.parse_args()
    if not args.base and not args.dry_run:
        print(
            "ERROR: リポジトリ直下の .env に ATTEND_SERVER= を書くか、--base で URL を指定してください。",
            file=sys.stderr,
        )
        return 2

    base = (args.base or os.environ.get("ATTEND_SERVER", "") or "http://SET_BASE_URL").rstrip("/")
    print(f"BASE={base}\n")

    if args.dry_run:
        print("=== DELETE ===")
        for sid in DELETE_STUDENT_IDS:
            print(f"DELETE {base}/api/students/{sid}")
        print("\n=== POST /api/coretime ===")
        for sid, (a, b, c, d) in CORETIME_BY_STUDENT.items():
            print(f"{sid} -> {a},{b} / {c},{d}")
        return 0

    failed = False
    print("=== DELETE ===")
    for sid in DELETE_STUDENT_IDS:
        url = f"{base}/api/students/{urllib.parse.quote(sid, safe='')}"
        code, body = http_json("DELETE", url)
        if code == 200:
            print(f"OK DELETE {sid} -> {body}")
        else:
            failed = True
            print(f"NG DELETE {sid} HTTP {code} -> {body}")

    print("\n=== POST coretime ===")
    for sid, (c1d, c1p, c2d, c2p) in CORETIME_BY_STUDENT.items():
        url = f"{base}/api/coretime/{urllib.parse.quote(sid, safe='')}"
        payload = {
            "core_time_1_day": c1d,
            "core_time_1_period": c1p,
            "core_time_2_day": c2d,
            "core_time_2_period": c2p,
        }
        code, body = http_json("POST", url, payload)
        if code == 200:
            print(f"OK coretime {sid} -> {body}")
        else:
            failed = True
            print(f"NG coretime {sid} HTTP {code} -> {body}")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
