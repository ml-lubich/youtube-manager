@echo off
echo 🎵 YouTube Playlist Manager - Installation Script
echo =================================================

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python is not installed. Please install Python 3.7+ first.
    pause
    exit /b 1
)

echo ✅ Python found
python --version

REM Create virtual environment
echo 📦 Creating virtual environment...
python -m venv venv

REM Activate virtual environment
echo 🔄 Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo 📥 Installing dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt

echo.
echo 🎉 Installation completed successfully!
echo.
echo 📋 Next steps:
echo 1. Activate the virtual environment:
echo    venv\Scripts\activate.bat
echo.
echo 2. Set up your YouTube API credentials:
echo    - Go to https://console.cloud.google.com/
echo    - Create a project and enable YouTube Data API v3
echo    - Create OAuth 2.0 credentials
echo    - Download as 'credentials.json' and place in this directory
echo.
echo 3. Run the application:
echo    python main.py
echo.
echo 📖 For detailed instructions, see README.md
pause 