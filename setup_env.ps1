# UTF-8 encoding for PowerShell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "========================================" -ForegroundColor Green
Write-Host "Techave Attendance Management System Setup" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

Write-Host "1. Creating virtual environment..." -ForegroundColor Yellow
python -m venv venv

Write-Host "2. Activating virtual environment..." -ForegroundColor Yellow
& .\venv\Scripts\Activate.ps1

Write-Host "3. Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip

Write-Host "4. Installing basic dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt

Write-Host "5. Installing additional packages..." -ForegroundColor Yellow
pip install mysqlclient==2.2.0
pip install django-extensions==3.2.3
pip install django-debug-toolbar==4.2.0
pip install python-dotenv==1.0.0
pip install requests==2.31.0

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Setup completed successfully!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Activate virtual environment: .\venv\Scripts\Activate.ps1" -ForegroundColor White
Write-Host "2. Create database: CREATE DATABASE techave_ktkr;" -ForegroundColor White
Write-Host "3. Run migrations: python manage.py makemigrations" -ForegroundColor White
Write-Host "4. Apply migrations: python manage.py migrate" -ForegroundColor White
Write-Host "5. Create superuser: python manage.py createsuperuser" -ForegroundColor White
Write-Host "6. Start server: python manage.py runserver" -ForegroundColor White
Write-Host ""
Write-Host "Note: Make sure MySQL and Redis servers are running." -ForegroundColor Red
Write-Host ""
Read-Host "Press Enter to continue" 