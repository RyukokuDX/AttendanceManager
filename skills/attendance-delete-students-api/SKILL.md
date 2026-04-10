---
name: attendance-delete-students-api
description: >-
  Deletes AttendanceManager students by student_id or by matching surnames in name
  via GET /api/students/ and DELETE /api/students/{student_id}. Explains that
  deletion removes Alert (violation) history and related logs. Use when removing
  students from the system or cleaning test data through the API.
---

# AttendanceManager 学生削除・違反データの扱い

## API

- **削除**: `DELETE /api/students/{student_id}`
- **一覧（氏名・学籍番号の解決）**: `GET /api/students/`

実装: `server/backend/main.py` の `delete_student`。

## 削除時に消えるもの（違反の初期化）

次の順で削除され、**コアタイム違反の Alert 行も消える**ため、当該学生の違反履歴は残らない。

1. `AttendanceLog`（出席記録）
2. `CurrentStatus`（現在の入室状況）
3. `Alert`（コアタイム違反など）
4. `Student` 本体

`Student.core_time_violations` はレコードごと削除される。**「削除せず違反回数だけ 0 に戻す」専用の REST はない**。その場合は DB 直接操作や別途 API 追加が必要（Alert を消し `core_time_violations` を 0 に揃える、など）。

## エージェントの手順

1. ベース URL を決める（Docker 例: `http://localhost:8889`。`server/docker-compose.yml` のポートに合わせる）。
2. `GET {base}/api/students/` で一覧を取得する。
3. ユーザーが氏名（苗字のみなど）で指定した場合は、`name` フィールドへの**部分一致**で `student_id` を特定する。同名がいないか確認する。
4. 各 `student_id` に対し `DELETE {base}/api/students/{student_id}` を実行する。`student_id` に要約記号が含まれる場合は URL エンコードする。
5. 応答を確認: 成功時は JSON で `status` / `message`（実装参照）。404 は対象なし。
6. **Telegram**: 削除成功時、実装により通知が飛ぶ可能性がある（運用環境の `TELEGRAM_*` 設定）。

## ユーティリティスクリプト

苗字の部分一致でまとめて削除する（ローカル検証・運用ツール用）。リポジトリルートから:

```bash
python skills/attendance-delete-students-api/scripts/delete_by_surnames.py 奥野 松本 石原 森川 藤井
```

- `.env` の `ATTEND_SERVER` がデフォルトのベース URL になる。上書きするときだけ `--base "http://..."`。
- 一致がなければ終了コード 1（何も削除しない）。
- API に届かなければ終了コード 2。

## curl 例

```bash
curl -X DELETE "${BASE}/api/students/${STUDENT_ID}"
```

## 注意

- **復元不能**: 削除は戻せない。本番では事前にバックアップまたは一覧の保存を推奨。
- **苗字だけの指定**は誤爆しうるため、可能ならフルネームまたは `student_id` をユーザーに確認する。

## 学籍番号ヒントに基づく一括処理

提示された `y24m001` 形式の ID で「5 名削除＋6 名コアタイム更新」をまとめて行う場合は、リポジトリ直下の `scripts/attendance_hint_batch.py` を使う。

- **推奨**: リポジトリ直下の `.env` に `ATTEND_SERVER=http://ホスト:8889`（末尾スラッシュ不要）を記載する。`.env.example` を参考にコピーしてよい。
- シェルに既に `ATTEND_SERVER` がある場合は **`.env` より優先**（上書きしない）。
- 一時的に別 URL へ向けるときだけ `--base` を付ける。
- 内容確認のみ: `python scripts/attendance_hint_batch.py --dry-run`

## 本スキルの置き場

このリポジトリでは **リポジトリ直下の `skills/<skill-name>/SKILL.md`** に置く。
