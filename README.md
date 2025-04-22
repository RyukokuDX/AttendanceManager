# 出席管理システム

## 概要
このシステムは、学生の出席状況を管理し、コアタイムの遵守状況を監視するためのWebアプリケーションです。

## 機能
- 学生の入退室管理
- コアタイム設定と監視
- 出席履歴の記録と表示
- コアタイム違反の検出と通知
- Telegram通知機能（入退室時の自動通知）
- 毎日0時の入室状況自動リセット

## 自動実行タスク（Cron）
システムは以下のスケジュールで自動タスクを実行します：

### ログ管理
- 毎月1日の午前0時に、前月のログを `/var/log/cron_YYYYMM.log` に保存し、現在のログファイルをクリアします。

### 入室状況の自動リセット
- 毎日0時に全学生の入室状況をリセットします
- リセットされた学生のリストをTelegramで通知します

### コアタイムチェック
以下の時間にコアタイムチェックを実行し、結果をログに記録します：
- 月曜から金曜の09:16 - 1限のコアタイムチェック
- 月曜から金曜の11:01 - 2限のコアタイムチェック
- 月曜から金曜の13:31 - 3限のコアタイムチェック
- 月曜から金曜の15:16 - 4限のコアタイムチェック
- 月曜から金曜の16:01 - 5限のコアタイムチェック

各コアタイムチェックの実行時には、以下の情報がログに記録されます：
- 開始時刻（[START]）
- APIレスポンス
- 終了時刻（[END]）

### crontabの設置場所
crontabファイルは以下の場所に設置されています：
- ソースコード: `server/backend/crontab`
- コンテナ内: `/etc/cron.d/app-cron`

コンテナ起動時に、Dockerfile内の以下の処理によりcrontabが設定されます：
```dockerfile
# cronの設定
COPY backend/crontab /etc/cron.d/app-cron
RUN echo "" >> /etc/cron.d/app-cron && \
    chmod 0644 /etc/cron.d/app-cron && \
    crontab /etc/cron.d/app-cron
```

### cronの注意事項
- **Windows/Mac環境での注意**: WindowsやMacでDockerを使用している場合、crontab内の`localhost`が正しく解決されない可能性があります。この場合は、`localhost`の代わりに`host.docker.internal`を使用するか、コンテナ名（例：`attend_app`）を使用してください。
- **タイムゾーンの確認**: cronが期待通りに動作しない場合は、コンテナ内の`/etc/localtime`の設定が実際のタイムゾーンと一致しているか確認してください。タイムゾーンがずれていると、スケジュールされた時間にタスクが実行されない可能性があります。
- **環境変数の設定**: cronで実行されるスクリプトは環境変数`ATTEND_SERVER`を使用してAPIサーバーにアクセスします。この環境変数が正しく設定されていることを確認してください。

## APIエンドポイント

### 学生管理API
- `POST /api/students/` - 新規学生の登録
  - 入力: `{"student_id": "string", "name": "string"}`
  - 出力: 登録された学生情報（ID、名前）
- `GET /api/students/` - 全学生の一覧取得
  - 出力: 学生情報の配列 `[{"student_id": "string", "name": "string", ...}]`
- `GET /api/students/{student_id}` - 特定の学生の情報取得
  - 出力: 学生情報 `{"student_id": "string", "name": "string", ...}`
- `DELETE /api/students/{student_id}` - 指定された学生の削除
  - 機能: 学生のレコードと関連する全てのデータ（出席記録、入室状況、コアタイム違反記録）を削除
  - 出力: `{"status": "success", "message": "学生ID {student_id} のレコードを削除しました"}`
  - 通知: 削除時にTelegramで通知を送信

### 入退室管理API
- `POST /api/attendance/` - 入退室記録の登録
  - 入力: `{"student_id": "string", "time": "datetime"}`
  - 出力: `{"name": "string", "status": "入室" | "退室"}`
- `GET /api/attendance/{student_id}` - 特定の学生の出席履歴取得
  - クエリパラメータ: `days` (オプション) - 過去何日分の履歴を取得するか
  - 出力: 出席記録の配列 `[{"student_id": "string", "entry_time": "datetime", "exit_time": "datetime"}]`
- `GET /api/current-status/` - 現在の入室状況一覧取得
  - 出力: 入室状況の配列 `[{"student_id": "string", "entry_time": "datetime"}]`
- `POST /api/attendance-now/{student_id}` - 現在時刻での入退室記録
  - 出力: `{"name": "string", "status": "入室" | "退室"}`
- `POST /api/reset-status` - 入室状況のリセット
  - 機能: 全学生の入室状況をリセット
  - 出力: 
    ```json
    {
        "status": "success",
        "message": "入室状況をリセットしました。",
        "reset_students": [
            "・学生名さん（学籍番号：XXXXXX）",
            ...
        ]
    }
    ```

### コアタイム管理API
- `GET /api/core-time/check/{period}` - 特定の時限のコアタイム遵守状況チェック
  - パラメータ: `period` (1-5) - チェックする時限
  - 出力: 
    ```json
    {
      "violations": ["student_id1", "student_id2", ...],
      "updated_students": [
        {
          "student_id": "string",
          "core_time_violations": integer
        }
      ]
    }
    ```
  - 機能: 
    - コアタイム違反を検出すると、Telegramに自動通知を送信
    - 違反が見つかった場合、Alertテーブルに記録
    - 学生の違反回数（core_time_violations）を更新
- `GET /api/core-time/violations` - コアタイム違反履歴の取得
  - 出力: アラートの配列 `[{"student_id": "string", "alert_date": "date", "alert_period": integer, "id": integer}]`

### コアタイム設定API
- `POST /api/coretime/{student_id}` - 学生のコアタイム設定
  - 入力: 
    ```json
    {
      "core_time_1_day": integer,    // 1:月曜 2:火曜 3:水曜 4:木曜 5:金曜 6:土曜 7:日曜
      "core_time_1_period": integer, // 1:1限 2:2限 3:3限 4:4限
      "core_time_2_day": integer,    // 1:月曜 2:火曜 3:水曜 4:木曜 5:金曜 6:土曜 7:日曜
      "core_time_2_period": integer  // 1:1限 2:2限 3:3限 4:4限
    }
    ```
  - 出力: `{"status": "success", "message": "コアタイムを設定しました"}`
- `GET /api/coretime/{student_id}` - 学生のコアタイム設定取得
  - 出力: 
    ```json
    {
      "core_time_1_day": integer,    // 1:月曜 2:火曜 3:水曜 4:木曜 5:金曜 6:土曜 7:日曜
      "core_time_1_period": integer, // 1:1限 2:2限 3:3限 4:4限
      "core_time_2_day": integer,    // 1:月曜 2:火曜 3:水曜 4:木曜 5:金曜 6:土曜 7:日曜
      "core_time_2_period": integer  // 1:1限 2:2限 3:3限 4:4限
    }
    ```

## データベース
SQLiteデータベースを使用し、以下のテーブルを管理します：
- Student（学生情報）
  - student_id (PK)
  - name
  - core_time_1_day
  - core_time_1_period
  - core_time_2_day
  - core_time_2_period
  - core_time_violations
- AttendanceLog（出席記録）
  - id (PK)
  - student_id (FK)
  - entry_time
  - exit_time
- CurrentStatus（現在の入室状況）
  - student_id (PK)
  - entry_time
- Alert（コアタイム違反等のアラート）
  - id (PK)
  - student_id (FK)
  - alert_date
  - alert_period

## 開発環境
- Python 3.8以上
- FastAPI
- SQLAlchemy
- SQLite

## セットアップ
1. Dockerコンテナの起動
```bash
docker-compose up -d
```

2. データベースの初期化
```bash
docker-compose exec app python -c "from db.database import Base, engine; from models.models import Student, AttendanceLog, CurrentStatus, Alert; Base.metadata.create_all(bind=engine)"
```

## システム設定
- タイムゾーン: 日本時間（JST）に設定（`/etc/localtime`を`Asia/Tokyo`に設定）
- cronジョブ: 日本時間に基づいて実行
- ログ: 日本時間で記録
- コンテナ設定:
  - ホスト名: attend_app
  - 環境変数: 
    - `TELEGRAM_ID`: TelegramボットのID
    - `TELEGRAM_ALERT`: 通知を送信するチャットID
  - ボリュームマウント:
    - ログ: `/var/log/cron.log`
    - データベース: `/app/db/attendance.db`

## 注意事項
- 本番環境では適切なセキュリティ設定が必要です
- CORSの設定は開発環境用の設定となっています
- Telegram通知機能を使用する場合は、システムの環境変数に以下の設定が必要です：
  - `TELEGRAM_ID`: TelegramボットのID
  - `TELEGRAM_ALERT`: 通知を送信するチャットID

## フロントエンド機能
- リアルタイムの出席状況表示
- 学生の入室・退室記録
- 出席履歴の表示
- コアタイム違反の表示
- アラート通知

## フロントエンド実装詳細 (app.js)

### 概要
app.jsは出席管理システムのフロントエンド部分を担当するJavaScriptファイルです。学生の出席状況をリアルタイムで表示し、定期的にデータを更新します。

### 主要機能
- **自動データ更新**: ページ読み込み時にデータを取得し、1分ごとに自動更新
- **学生データ表示**: 学生ID、名前、現在の入室状況、今週の利用時間、コアタイム情報を表示
- **コアタイム管理**: 学生ごとのコアタイム情報（曜日と時限）を表示
- **エラーハンドリング**: データ取得失敗時のエラー表示と再読み込み機能

### API連携
- `/api/students/`: 学生一覧の取得
- `/api/current-status/`: 現在の入室状況の取得
- `/api/attendance/{student_id}?days=7`: 学生ごとの出席履歴（過去7日間）の取得

### 表示項目
1. **学生ID**: 学生の識別番号
2. **名前**: 学生の氏名
3. **入室状況**: 「入室中」または「退室中」を表示（リアルタイム更新）
4. **利用時間**: 今週の合計利用時間（時間単位で小数点1桁まで表示）
5. **コアタイム1**: 1つ目のコアタイム（曜日と時限）
6. **コアタイム2**: 2つ目のコアタイム（曜日と時限）
7. **違反回数**: コアタイム違反の回数（違反がある場合は強調表示）

### データ更新ロジック
1. 学生一覧を取得
2. 現在の入室状況を取得
3. 今週の日付範囲を計算（日曜日から現在まで）
4. 各学生について:
   - 現在の入室状況を確認
   - 今週の出席履歴を取得
   - 利用時間を計算（入室時間と退室時間の差分）
   - コアタイム情報を整形して表示

### エラー処理
- APIリクエスト失敗時: エラーメッセージを表示し、再読み込みボタンを提供
- 個別の学生データ取得失敗時: エラーをログに記録し、他の学生のデータ表示は継続

### 関数仕様

#### 1. `loadStudentData()`
- **目的**: 学生データを取得し、画面に表示する
- **戻り値**: なし（非同期関数）
- **処理内容**:
  1. 学生一覧をAPIから取得
  2. 現在の入室状況をAPIから取得
  3. 今週の日付範囲を計算（日曜日から現在まで）
  4. 各学生について:
     - 現在の入室状況を確認
     - 今週の出席履歴を取得
     - 利用時間を計算
     - コアタイム情報を整形
     - テーブル行を作成して表示
- **エラー処理**:
  - APIリクエスト失敗時: エラーメッセージを表示し、再読み込みボタンを提供
  - 個別の学生データ取得失敗時: エラーをログに記録し、他の学生のデータ表示は継続

#### 2. `formatCoreTime(day, period)`
- **目的**: コアタイムの曜日と時限を日本語表記に整形する
- **引数**:
  - `day`: 曜日を表す数値（0: 日曜日, 1: 月曜日, ..., 6: 土曜日）
  - `period`: 時限を表す数値（1: 1限, 2: 2限, ..., 4: 4限）
- **戻り値**: 整形されたコアタイム文字列

## クライアントプログラム（AttendanceManager.py）

### 概要
AttendanceManager.pyは、NFCリーダーを使用して学生の入退室を記録するクライアントプログラムです。このプログラムは、S380 NFCリーダーとFelicaカードを使用して学生の出席状況を管理します。

### ハードウェア要件
- **NFCリーダー**: S380
- **カード**: Felica（学生証など）

### カード読み取りプロセス
1. 学生がFelicaカードをリーダーにかざすと、プログラムはカードのIDを読み取ります。
2. 読み取られたIDは以下の処理を行います：
   - 学生の場合、前後2文字を削除します（例：`01x1234567801` → `x12345678`）
   - その後、NULL文字（`\x00`）を削除します
3. 処理されたIDを使用して、APIサーバーに出席データを送信します
4. サーバーからのレスポンスに基づいて、学生の入退室状況を画面に表示します

### 技術的な詳細
- **システムコード**: `0x809E`（Felicaカードのシステムコード）
- **データブロック読み取り**: サービスコード`106`、ブロックコード`0`から学生IDを読み取ります

### 使用方法
1. 環境変数`ATTEND_SERVER`にAPIサーバーのアドレスを設定します
2. プログラムを実行します：`python AttendanceManager.py`
3. 画面に表示される指示に従って、学生がカードをリーダーにかざします
4. 入退室記録が自動的にサーバーに送信され、結果が画面に表示されます

### エラー処理
- NFCリーダーの接続エラー
- カード読み取りエラー
- APIサーバーとの通信エラー
- 各エラーは画面に表示され、ログファイル（`attend.log`）に記録されます