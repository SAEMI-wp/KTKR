@echo off
echo 仮想環境をアクティベートしています...
call venv\Scripts\activate.bat
echo 仮想環境がアクティベートされました！
echo 現在のPythonパス: %VIRTUAL_ENV%
cmd /k 