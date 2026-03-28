@echo off
chcp 65001 >nul
echo.
echo ╔══════════════════════════════════════════════╗
echo ║  🇹🇭 RouterAI + OpenClaw Thai Dashboard      ║
echo ║  Windows Setup                               ║
echo ╚══════════════════════════════════════════════╝
echo.

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ ไม่พบ Python! ดาวน์โหลดที่ https://python.org
    pause
    exit /b 1
)

where git >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ ไม่พบ Git! ดาวน์โหลดที่ https://git-scm.com
    pause
    exit /b 1
)

echo [1/4] ดาวน์โหลดโค้ด...
cd /d %USERPROFILE%
if exist routerai (
    echo พบโฟลเดอร์เดิม กำลังอัปเดต...
    cd routerai
    git pull
) else (
    git clone "https://github.com/tenotony/--RouterAI.git" routerai
    cd routerai
)

echo [2/4] สร้าง Virtual Environment...
python -m venv venv
call venv\Scripts\activate

echo [3/4] ติดตั้ง Dependencies...
pip install -r requirements.txt -q

echo [4/4] ตั้งค่า...
if not exist api_keys.json echo {} > api_keys.json
if not exist .env copy .env.example .env

echo.
echo ✅ ติดตั้งสำเร็จ!
echo.
echo เริ่มใช้งาน:
echo   venv\Scripts\activate
echo   python src\proxy.py
echo.
echo 📊 Dashboard: http://localhost:8899/dashboard/
echo 🔀 API Proxy: http://localhost:8900
echo.
pause
