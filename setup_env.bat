@echo off
echo ========================================
echo Techave 勤怠管理システム 環境セットアップ
echo ========================================
echo.

echo 1. 仮想環境を作成中...
python -m venv venv

echo 2. 仮想環境をアクティベート中...
call venv\Scripts\activate.bat

echo 3. pipをアップグレード中...
python -m pip install --upgrade pip

echo 4. 基本依存関係をインストール中...
pip install -r requirements.txt

echo 5. 追加パッケージをインストール中...
pip install mysqlclient==2.2.0
pip install django-extensions==3.2.3
pip install django-debug-toolbar==4.2.0
pip install python-dotenv==1.0.0
pip install requests==2.31.0

echo.
echo ========================================
echo セットアップが完了しました！
echo ========================================
echo.
echo 次のステップ:
echo 1. 仮想環境をアクティベート: venv\Scripts\activate.bat
echo 2. データベースを作成: CREATE DATABASE techave_ktkr;
echo 3. マイグレーション実行: python manage.py makemigrations
echo 4. マイグレーション適用: python manage.py migrate
echo 5. スーパーユーザー作成: python manage.py createsuperuser
echo 6. サーバー起動: python manage.py runserver
echo.
echo 注意: MySQL と Redis サーバーが起動していることを確認してください。
echo.
pause 