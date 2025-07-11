@echo off
echo Quick Setup for Techave Attendance System
echo ========================================

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install packages
echo Installing packages...
pip install --upgrade pip
pip install -r requirements.txt

echo.
echo Setup completed! 
echo To activate: venv\Scripts\activate.bat
echo To run server: python manage.py runserver
echo.
pause 