@echo off
chcp 65001 >nul 2>&1
echo.
echo ╔══════════════════════════════════════╗
echo ║     🔀 RouterAI - Starting...        ║
echo ║     กำลังเริ่มระบบ                    ║
echo ╚══════════════════════════════════════╝
echo.

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ ไม่พบ Python - กรุณาติดตั้ง Python 3.10+
    pause
    exit /b 1
)

:: Check/install packages
python -c "import fastapi" >nul 2>&1
if %errorlevel% neq 0 (
    echo 📦 กำลังติดตั้ง packages...
    pip install fastapi uvicorn httpx
)

echo 🚀 เริ่ม Proxy Server ที่ port 8900...
start "RouterAI Proxy" python src\proxy.py --port 8900

timeout /t 2 /nobreak >nul

echo 🚀 เริ่ม Dashboard ที่ port 8899...
start "RouterAI Dashboard" python src\dashboard.py --port 8899

timeout /t 2 /nobreak >nul

echo.
echo ✅ RouterAI พร้อมใช้งานแล้ว!
echo.
echo   📊 Dashboard:  http://127.0.0.1:8899
echo   🔀 Proxy API:  http://127.0.0.1:8900
echo.
echo   เปิด Browser ไปที่ http://127.0.0.1:8899
echo.
pause
