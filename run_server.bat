@echo off
echo Djangoサーバーを起動しています...

REM 仮想環境をアクティベート
call venv\Scripts\activate.bat

REM Djangoサーバーを起動
python manage.py runserver

pause 