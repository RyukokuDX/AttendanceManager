---
name: attendance-coretime-api
description: >-
  Changes or reads student core time (コアタイム) for AttendanceManager via HTTP API.
  Use when the user asks to set/update/get core time through the API, curl, scripts,
  or integration outside the web UI; references server/backend FastAPI routes.
---

# AttendanceManager コアタイム API

## 前提

- バックエンドは FastAPI（`server/backend/main.py`）。Docker 利用時は `server/docker-compose.yml` でホスト `8889` → コンテナ `8000`。
- **ベース URL** はリポジトリ直下の `.env` の `ATTEND_SERVER` に書く方式を推奨（`scripts/attendance_hint_batch.py` が起動時に読み込む）。従来どおりシェルの環境変数や `--base` でも指定可。
- 認証ヘッダは現状の実装では不要（CORS は広め）。本番の制限がある場合はユーザーに確認する。

## 取得（現在値の確認）

`GET /api/coretime/{student_id}`

成功時の JSON キー（実装どおり）:

- `core_time_1_day`, `core_time_1_period`, `core_time_2_day`, `core_time_2_period`

404: 学生が存在しない。

## 変更

`POST /api/coretime/{student_id}`  
`Content-Type: application/json`

ボディは **4 フィールドすべて必須**（Pydantic `CoreTimeUpdate` / `server/backend/schemas/schemas.py`）。

| フィールド | 意味 |
|------------|------|
| `core_time_1_day` | コアタイム1の曜日 |
| `core_time_1_period` | コアタイム1の時限 |
| `core_time_2_day` | コアタイム2の曜日 |
| `core_time_2_period` | コアタイム2の時限 |

**曜日**: `1` = 月 … `7` = 日（`check_core_time` は `weekday()+1` と一致）。

**時限**: プロジェクト README では 1〜4 限の例。DB スキーマコメントにはより大きい時限の記述があるため、運用ルールがあればユーザー確認。API 上は整数で受け付ける。

成功レスポンス（実装どおり）:

```json
{"message": "Core time updated successfully"}
```

失敗: 404（学生なし）、500（その他。`detail` を確認）。

## エージェントの手順

1. `student_id` を確定する（ユーザー指定または一覧 API 等で取得）。
2. 変更前に必要なら `GET` で現状を記録または表示。
3. `POST` で 4 フィールドをすべて送る（部分更新はないため、片方だけ変える場合も既存値を読んでからマージする）。
4. ステータスコードとレスポンス本文をユーザーに伝える。

## curl 例

置き換え: `BASE`, `STUDENT_ID`。

```bash
curl -sS "${BASE}/api/coretime/${STUDENT_ID}"

curl -sS -X POST "${BASE}/api/coretime/${STUDENT_ID}" \
  -H "Content-Type: application/json" \
  -d '{"core_time_1_day":1,"core_time_1_period":1,"core_time_2_day":3,"core_time_2_period":2}'
```

## 関連（コアタイムだが「変更」ではない）

- `GET /api/core-time/check/{period}` … 指定時限のコアタイム対象チェック（管理用）。
- コアタイム設定の更新は **`/api/coretime/...`**（ハイフンなし）を使う。

## 実装参照

- ルート: `server/backend/main.py`（`set_coretime`, `get_coretime`）
- スキーマ: `server/backend/schemas/schemas.py`（`CoreTimeUpdate`）

複数学生を学籍番号でまとめて更新する例: `scripts/attendance_hint_batch.py`（コアタイム部分。削除も同梱）。

## 本スキルの置き場

このリポジトリでは **リポジトリ直下の `skills/<skill-name>/SKILL.md`** に置く（例: `skills/attendance-coretime-api/SKILL.md`）。
