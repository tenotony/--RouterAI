@echo off
chcp 65001 >nul 2>&1
echo.
echo ╔══════════════════════════════════════╗
echo ║     🔀 RouterAI - Windows Setup      ║
echo ║     ติดตั้งสำหรับ Windows            ║
echo ╚══════════════════════════════════════╝
echo.

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ ไม่พบ Python - กรุณาติดตั้ง Python 3.10+ จาก python.org
    pause
    exit /b 1
)

:: Clone or update
if exist "RouterAI" (
    echo 📂 พบโฟลเดอร์เดิม กำลังอัปเดต...
    cd RouterAI
    git pull
) else (
    echo 📥 กำลังดาวน์โหลด RouterAI...
    git clone https://github.com/tenotony/RouterAI.git
    cd RouterAI
)

:: Create venv
echo 🐍 กำลังสร้าง Virtual Environment...
python -m venv venv
call venv\Scripts\activate.bat

:: Install
echo 📦 กำลังติดตั้ง packages...
pip install --upgrade pip
pip install -r requirements.txt

:: Create default config
if not exist "api_keys.json" (
    echo {} > api_keys.json
)

echo.
echo ✅ ติดตั้งสำเร็จ!
echo.
echo 📋 ขั้นตอนต่อไป:
echo.
echo   1. ตั้งค่า API Key:
echo      python routerai setup
echo.
echo   2. เริ่ม Proxy (Terminal 1):
echo      python src\proxy.py
echo.
echo   3. เริ่ม Dashboard (Terminal 2):
echo      python src\dashboard.py
echo.
echo   4. เปิด Browser: http://127.0.0.1:8899
echo.
pause
