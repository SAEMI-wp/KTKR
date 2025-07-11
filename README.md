# Techave 勤怠管理システム

## プロジェクト概要
Djangoベースの勤怠管理システムです。従業員の出勤管理、レポート生成、管理者ダッシュボード機能を提供します。

## 技術スタック
- **Backend**: Django 4.2.7
- **Database**: MySQL 8.0+
- **Cache**: Redis 6.0+
- **Frontend**: Bootstrap 5
- **PDF生成**: ReportLab
- **Excel操作**: OpenPyXL
- **Python**: 3.11+

## 必要なソフトウェア
- **Python 3.11+**
- **MySQL 8.0+**
- **Redis 6.0+**
- **Git**

## セットアップ手順

### 1. 仮想環境のセットアップ

#### Windows (PowerShell)
```powershell
# PowerShell実行ポリシーを変更（初回のみ）
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 自動セットアップ
.\setup_env.ps1
```

#### Windows (Command Prompt)
```cmd
# 自動セットアップ
setup_env.bat
```

#### 手動セットアップ
```bash
# 仮想環境作成
python -m venv venv

# 仮想環境アクティベート
venv\Scripts\activate.bat  # Windows
source venv/bin/activate   # Linux/Mac

# 依存関係インストール
pip install -r requirements.txt
```

### 2. データベースの設定

#### MySQL データベース作成
```sql
CREATE DATABASE techave_ktkr CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

#### Redis 設定
Redis設定ファイル (`redis.conf`) に以下を追加：
```
requirepass techave_ktkr
```

### 3. 環境変数の設定

`.env`ファイルを作成し、以下の設定を追加：

```env
# Django設定
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# データベース設定
DB_NAME=techave_ktkr
DB_USER=root
DB_PASSWORD=root.root
DB_HOST=localhost
DB_PORT=3306

# メール設定
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Redis設定
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_PASSWORD=techave
```

### 4. Djangoの初期化

```bash
# 仮想環境アクティベート
venv\Scripts\activate.bat

# マイグレーション作成
python manage.py makemigrations

# マイグレーション適用
python manage.py migrate

# スーパーユーザー作成
python manage.py createsuperuser

# 静的ファイル収集
python manage.py collectstatic
```

### 5. サーバーの起動

```bash
# 自動起動
run_server.bat

# または手動で実行
python manage.py runserver
```

## 使用方法

### 仮想環境のアクティベート
```bash
# Windows
venv\Scripts\activate.bat

# PowerShell
.\venv\Scripts\Activate.ps1
```

### Djangoサーバーの起動
```bash
run_server.bat
```

## 主な機能
- 従業員の出勤・退勤記録
- 勤怠レポート生成（PDF/Excel）
- 管理者ダッシュボード
- カレンダー表示
- メール通知機能
- Redis キャッシュ機能

## トラブルシューティング

### MySQL 接続エラー
- MySQL サーバーが起動していることを確認
- データベース `techave_ktkr` が作成されていることを確認
- ユーザー名とパスワードが正しいことを確認

### Redis 接続エラー
- Redis サーバーが起動していることを確認
- パスワード設定が正しいことを確認

### PowerShell 実行エラー
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## 注意事項
- MySQL サーバーが必要です
- Redis サーバーが必要です（キャッシュ機能用）
- Gmail の2段階認証アプリパスワードが必要です（メール機能用）
- Python 3.11以上が必要です 