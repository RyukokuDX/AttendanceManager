# Agent 向け

## スキルは「悪い」のではなく、読まないと効かない

自作スキルやリポジトリの `skills/` の内容は、**関連タスクで `Read` するまでコンテキストに入らない**。探索失敗や配置の混乱は、多くの場合 **読みに行っていない・パスが会話に出ていない**ことが原因になりうる。疑う前に該当 `SKILL.md` を開くこと。

## 作業前に読むスキル（条件付き）

### スキルの新規作成・SKILL.md の書き方・置き場の判断

Cursor 同梱の **create-skill** を必ず `Read` してから着手する。

- Windows: `%USERPROFILE%\.cursor\skills-cursor\create-skill\SKILL.md`
- macOS / Linux: `~/.cursor/skills-cursor/create-skill/SKILL.md`

### 本リポジトリの出席管理 API まわり

次を必要に応じて `Read` する（パスはリポジトリルートからの相対）。

- `skills/attendance-coretime-api/SKILL.md` … コアタイム API
- `skills/attendance-delete-students-api/SKILL.md` … 学生削除・違反データ
- `skills/attendance-delete-students-api/scripts/delete_by_surnames.py` … 苗字一致削除スクリプト

一括処理（`.env` の `ATTEND_SERVER`）: `scripts/attendance_hint_batch.py`

### ユーザースキル（my-skills 等）

パスは環境依存。ユーザーがパスを示したとき、またはワークスペースに含まれるときはその `SKILL.md` を `Read` する。

## プロジェクトのその他

- ルートに `cursor.md` は無い。本ファイル（`agent.md`）と `.cursor/rules`（あれば）を優先する。
