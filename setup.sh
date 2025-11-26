#!/bin/bash

# MediSafe+ Project Setup Script for macOS/Linux
# This script automates the installation process

echo ""
echo "============================================"
echo "   MediSafe+ Project Setup"
echo "============================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 is not installed"
    echo "Please install Python 3.9+ from https://www.python.org/downloads/"
    exit 1
fi

echo "[✓] Python is installed"
python3 --version
echo ""

# Create virtual environment
echo "[*] Creating virtual environment..."
python3 -m venv venv
if [ $? -ne 0 ]; then
    echo "[ERROR] Failed to create virtual environment"
    exit 1
fi
echo "[✓] Virtual environment created"
echo ""

# Activate virtual environment
echo "[*] Activating virtual environment..."
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo "[ERROR] Failed to activate virtual environment"
    exit 1
fi
echo "[✓] Virtual environment activated"
echo ""

# Upgrade pip
echo "[*] Upgrading pip..."
python -m pip install --upgrade pip
if [ $? -ne 0 ]; then
    echo "[WARNING] pip upgrade had issues, continuing anyway..."
fi
echo "[✓] pip upgraded"
echo ""

# Install requirements
if [ -f requirements.txt ]; then
    echo "[*] Installing dependencies from requirements.txt..."
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "[ERROR] Failed to install dependencies"
        exit 1
    fi
    echo "[✓] Dependencies installed successfully"
else
    echo "[*] requirements.txt not found, installing individual packages..."
    echo "[*] Installing Django..."
    pip install Django==5.2.6
    
    echo "[*] Installing database drivers..."
    pip install psycopg2-binary==2.9.10 pillow==11.3.0
    
    echo "[*] Installing other dependencies..."
    pip install python-dotenv requests supabase cryptography
    
    echo "[✓] Core packages installed"
fi
echo ""

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "[*] Creating .env template file..."
    cat > .env << 'EOF'
# Django Configuration
DJANGO_SECRET_KEY=django-insecure-^_^z+g@c_wo-@$zq%wx4e^#9l2$)!=^rhv6=jqq_32ele0b107
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost,testserver

# Database Configuration - PostgreSQL (Supabase)
DB_ENGINE=django.db.backends.postgresql
DB_NAME=postgres
DB_USER=postgres.YOUR_SUPABASE_USER
DB_PASSWORD=YOUR_SUPABASE_PASSWORD
DB_HOST=aws-1-ap-southeast-1.pooler.supabase.com
DB_PORT=5432
DB_SSLMODE=require
DB_CONN_MAX_AGE=0
EOF
    echo "[✓] .env file created - PLEASE UPDATE WITH YOUR DATABASE CREDENTIALS"
else
    echo "[✓] .env file already exists"
fi
echo ""

# Run migrations
echo "[*] Running database migrations..."
python manage.py migrate
if [ $? -ne 0 ]; then
    echo "[WARNING] Migrations had issues. This may be due to database connection."
    echo "Please verify your .env database credentials and run: python manage.py migrate"
else
    echo "[✓] Migrations completed successfully"
fi
echo ""

# Create superuser
echo "[*] Creating superuser account..."
echo ""
echo "Please provide details for the admin account:"
python manage.py createsuperuser
echo ""

# Final summary
echo ""
echo "============================================"
echo "   Setup Complete!"
echo "============================================"
echo ""
echo "[✓] Virtual environment ready"
echo "[✓] Dependencies installed"
echo "[✓] Database configured"
echo ""
echo "Next steps:"
echo "1. Update .env file with your Supabase credentials (if not done)"
echo "2. Run: python manage.py runserver"
echo "3. Visit: http://127.0.0.1:8000"
echo "4. Admin: http://127.0.0.1:8000/admin"
echo ""
echo "To activate virtual environment in future sessions, run:"
echo "   source venv/bin/activate"
echo ""
