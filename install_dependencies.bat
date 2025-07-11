@echo off
echo 依存関係をインストール中...

REM 仮想環境をアクティベート
call venv\Scripts\activate.bat

REM 基本パッケージをインストール
pip install -r requirements.txt

REM MySQL クライアント (Windows用)
pip install mysqlclient==2.2.0

REM 開発用ツール
pip install django-extensions==3.2.3
pip install django-debug-toolbar==4.2.0

REM 環境変数管理
pip install python-dotenv==1.0.0

REM HTTP リクエスト
pip install requests==2.31.0

echo インストール完了！
pause 