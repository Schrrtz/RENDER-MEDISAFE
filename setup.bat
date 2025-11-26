@echo off
REM MediSafe+ Project Setup Script for Windows
REM This script automates the installation process

echo.
echo ============================================
echo   MediSafe+ Project Setup
echo ============================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.9+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [✓] Python is installed
python --version
echo.

REM Create virtual environment
echo [*] Creating virtual environment...
python -m venv venv
if %errorlevel% neq 0 (
    echo [ERROR] Failed to create virtual environment
    pause
    exit /b 1
)
echo [✓] Virtual environment created
echo.

REM Activate virtual environment
echo [*] Activating virtual environment...
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo [ERROR] Failed to activate virtual environment
    pause
    exit /b 1
)
echo [✓] Virtual environment activated
echo.

REM Upgrade pip
echo [*] Upgrading pip...
python -m pip install --upgrade pip
if %errorlevel% neq 0 (
    echo [WARNING] pip upgrade had issues, continuing anyway...
)
echo [✓] pip upgraded
echo.

REM Install requirements
if exist requirements.txt (
    echo [*] Installing dependencies from requirements.txt...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install dependencies
        pause
        exit /b 1
    )
    echo [✓] Dependencies installed successfully
) else (
    echo [*] requirements.txt not found, installing individual packages...
    echo [*] Installing Django...
    pip install Django==5.2.6
    
    echo [*] Installing database drivers...
    pip install psycopg2-binary==2.9.10 pillow==11.3.0
    
    echo [*] Installing other dependencies...
    pip install python-dotenv requests supabase cryptography
    
    echo [✓] Core packages installed
)
echo.

REM Create .env file if it doesn't exist
if not exist .env (
    echo [*] Creating .env template file...
    (
        echo # Django Configuration
        echo DJANGO_SECRET_KEY=django-insecure-^_^z+g@c_wo-@$zq%%wx4e^#9l2$)!=^rhv6=jqq_32ele0b107
        echo DJANGO_DEBUG=True
        echo DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost,testserver
        echo.
        echo # Database Configuration - PostgreSQL (Supabase^)
        echo DB_ENGINE=django.db.backends.postgresql
        echo DB_NAME=postgres
        echo DB_USER=postgres.YOUR_SUPABASE_USER
        echo DB_PASSWORD=YOUR_SUPABASE_PASSWORD
        echo DB_HOST=aws-1-ap-southeast-1.pooler.supabase.com
        echo DB_PORT=5432
        echo DB_SSLMODE=require
        echo DB_CONN_MAX_AGE=0
    ) > .env
    echo [✓] .env file created - PLEASE UPDATE WITH YOUR DATABASE CREDENTIALS
) else (
    echo [✓] .env file already exists
)
echo.

REM Run migrations
echo [*] Running database migrations...
python manage.py migrate
if %errorlevel% neq 0 (
    echo [WARNING] Migrations had issues. This may be due to database connection.
    echo Please verify your .env database credentials and run: python manage.py migrate
) else (
    echo [✓] Migrations completed successfully
)
echo.

REM Create superuser
echo [*] Creating superuser account...
echo.
echo Please provide details for the admin account:
python manage.py createsuperuser
echo.

REM Final summary
echo.
echo ============================================
echo   Setup Complete!
echo ============================================
echo.
echo [✓] Virtual environment ready
echo [✓] Dependencies installed
echo [✓] Database configured
echo.
echo Next steps:
echo 1. Update .env file with your Supabase credentials (if not done)
echo 2. Run: python manage.py runserver
echo 3. Visit: http://127.0.0.1:8000
echo 4. Admin: http://127.0.0.1:8000/admin
echo.
echo To activate virtual environment in future sessions, run:
echo   .\venv\Scripts\activate.bat
echo.
pause
