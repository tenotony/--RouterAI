#!/bin/bash
# RouterAI - Start All Services
# รัน Proxy + Dashboard พร้อมกันในเครื่องเดียว

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo -e "${CYAN}╔══════════════════════════════════════╗${NC}"
echo -e "${CYAN}║     🔀 RouterAI - Starting...        ║${NC}"
echo -e "${CYAN}║     กำลังเริ่มระบบ                    ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════╝${NC}"
echo ""

# Check Python
PYTHON=""
if command -v python3 &> /dev/null; then
    PYTHON="python3"
elif command -v python &> /dev/null; then
    PYTHON="python"
else
    echo -e "${RED}❌ ไม่พบ Python - กรุณาติดตั้ง Python 3.10+${NC}"
    exit 1
fi

# Check venv
VENV_DIR="$PROJECT_DIR/venv"
if [ -d "$VENV_DIR" ]; then
    echo -e "${GREEN}✅ พบ Virtual Environment${NC}"
    source "$VENV_DIR/bin/activate"
else
    echo -e "${YELLOW}⚠️  ไม่พบ venv - ใช้ Python ระบบ${NC}"
    echo -e "   แนะนำ: รัน install.sh ก่อน เพื่อสร้าง venv"
fi

# Check dependencies
$PYTHON -c "import fastapi, uvicorn, httpx" 2>/dev/null || {
    echo -e "${YELLOW}📦 กำลังติดตั้ง Python packages...${NC}"
    $PYTHON -m pip install --break-system-packages -q fastapi uvicorn httpx 2>/dev/null || \
    pip install --break-system-packages -q fastapi uvicorn httpx 2>/dev/null || {
        echo -e "${RED}❌ ติดตั้ง packages ไม่สำเร็จ - รัน: pip install fastapi uvicorn httpx${NC}"
        exit 1
    }
}

# Check API keys
if [ -f "$PROJECT_DIR/api_keys.json" ]; then
    KEY_COUNT=$($PYTHON -c "
import json
with open('$PROJECT_DIR/api_keys.json') as f:
    keys = json.load(f)
print(sum(1 for v in keys.values() if v and v.strip()))
" 2>/dev/null || echo "0")
    if [ "$KEY_COUNT" = "0" ]; then
        echo -e "${YELLOW}⚠️  ยังไม่ได้ใส่ API Key!${NC}"
        echo -e "   รัน: ${CYAN}$PYTHON $PROJECT_DIR/routerai setup${NC}"
        echo -e "   หรือเปิด Dashboard แล้วใส่ที่แท็บ '🔑 ใส่ API Key'"
        echo ""
    else
        echo -e "${GREEN}✅ พบ API Key $KEY_COUNT ตัว${NC}"
    fi
fi

# Kill existing processes on ports
for PORT in 8900 8899; do
    PID=$(lsof -ti :$PORT 2>/dev/null || true)
    if [ -n "$PID" ]; then
        echo -e "${YELLOW}🔄 หยุด process เก่าที่ port $PORT (PID: $PID)${NC}"
        kill $PID 2>/dev/null || true
        sleep 1
    fi
done

# Start Proxy (background)
echo -e "${CYAN}🚀 เริ่ม Proxy Server ที่ port 8900...${NC}"
cd "$PROJECT_DIR"
$PYTHON src/proxy.py --host 127.0.0.1 --port 8900 &
PROXY_PID=$!
sleep 2

# Verify proxy started
if kill -0 $PROXY_PID 2>/dev/null; then
    echo -e "${GREEN}✅ Proxy ทำงานแล้ว (PID: $PROXY_PID)${NC}"
else
    echo -e "${RED}❌ Proxy เริ่มไม่สำเร็จ${NC}"
    exit 1
fi

# Start Dashboard (background)
echo -e "${CYAN}🚀 เริ่ม Dashboard ที่ port 8899...${NC}"
$PYTHON src/dashboard.py --host 127.0.0.1 --port 8899 &
DASH_PID=$!
sleep 2

# Verify dashboard started
if kill -0 $DASH_PID 2>/dev/null; then
    echo -e "${GREEN}✅ Dashboard ทำงานแล้ว (PID: $DASH_PID)${NC}"
else
    echo -e "${RED}❌ Dashboard เริ่มไม่สำเร็จ${NC}"
    kill $PROXY_PID 2>/dev/null || true
    exit 1
fi

echo ""
echo -e "${GREEN}╔══════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     ✅ RouterAI พร้อมใช้งานแล้ว!      ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════╝${NC}"
echo ""
echo -e "  📊 Dashboard:  ${CYAN}http://127.0.0.1:8899${NC}"
echo -e "  🔀 Proxy API:  ${CYAN}http://127.0.0.1:8900${NC}"
echo ""
echo -e "  ${YELLOW}ขั้นตอนต่อไป:${NC}"
echo -e "  1. เปิด Dashboard ใน Browser"
echo -e "  2. ไปที่แท็บ '🔑 ใส่ API Key' แล้วใส่ Key"
echo -e "  3. ไปที่แท็บ '🔌 เชื่อม OpenClaw' แล้วกดปุ่มเชื่อมต่อ"
echo -e "  4. รัน: ${CYAN}openclaw restart${NC}"
echo ""
echo -e "  ${YELLOW}กด Ctrl+C เพื่อหยุดทั้งหมด${NC}"
echo ""

# Save PIDs for cleanup
echo "$PROXY_PID $DASH_PID" > "$PROJECT_DIR/.routerai_pids"

# Wait for Ctrl+C
cleanup() {
    echo ""
    echo -e "${YELLOW}🛑 กำลังหยุด RouterAI...${NC}"
    kill $PROXY_PID 2>/dev/null || true
    kill $DASH_PID 2>/dev/null || true
    rm -f "$PROJECT_DIR/.routerai_pids"
    echo -e "${GREEN}✅ หยุดเรียบร้อย${NC}"
    exit 0
}
trap cleanup INT TERM

wait
