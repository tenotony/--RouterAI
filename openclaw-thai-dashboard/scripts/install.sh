#!/usr/bin/env bash
# ============================================================
# OpenClaw Thai Dashboard + API Router — One-Line Installer
# Usage: curl -fsSL https://raw.githubusercontent.com/.../install.sh | bash
# ============================================================
set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

REPO_URL="https://github.com/tenotony/--RouterAI.git"
INSTALL_DIR="$HOME/routerai"

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║${NC}  🇹🇭 ${GREEN}RouterAI + OpenClaw Thai Dashboard${NC}      ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}     รวม AI ฟรี + จัดการ OpenClaw ภาษาไทย   ${CYAN}║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════╝${NC}"
echo ""

# --- Check Python ---
echo -e "${YELLOW}[1/5] ตรวจสอบ Python...${NC}"
if command -v python3 &>/dev/null; then
    PYTHON="python3"
elif command -v python &>/dev/null; then
    PYTHON="python"
else
    echo -e "${RED}❌ ไม่พบ Python! กรุณาติดตั้ง Python 3.8+${NC}"
    echo "   Ubuntu/Debian: sudo apt install python3 python3-pip python3-venv"
    echo "   macOS: brew install python3"
    exit 1
fi
PY_VER=$($PYTHON -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "${GREEN}✅ Python $PY_VER${NC}"

# --- Check Git ---
echo -e "${YELLOW}[2/5] ตรวจสอบ Git...${NC}"
if ! command -v git &>/dev/null; then
    echo -e "${YELLOW}⚠️ ไม่พบ Git กำลังติดตั้ง...${NC}"
    if command -v apt &>/dev/null; then sudo apt install -y git; fi
fi
echo -e "${GREEN}✅ Git พร้อม${NC}"

# --- Download ---
echo -e "${YELLOW}[3/5] ดาวน์โหลดโค้ด...${NC}"
if [ -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}⚠️ พบโฟลเดอร์เดิม กำลังอัปเดต...${NC}"
    cd "$INSTALL_DIR" && git pull origin main 2>/dev/null || true
else
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi
echo -e "${GREEN}✅ ดาวน์โหลดสำเร็จ${NC}"

# --- Setup venv + install ---
echo -e "${YELLOW}[4/5] ติดตั้ง dependencies...${NC}"
$PYTHON -m venv venv
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo -e "${GREEN}✅ ติดตั้งสำเร็จ${NC}"

# --- Create api_keys.json ---
echo -e "${YELLOW}[5/5] ตั้งค่าเริ่มต้น...${NC}"
if [ ! -f api_keys.json ]; then
    echo '{}' > api_keys.json
    echo -e "${GREEN}✅ สร้าง api_keys.json${NC}"
fi

# --- Create start scripts ---
cat > start.sh << 'EOF'
#!/usr/bin/env bash
cd "$(dirname "$0")"
source venv/bin/activate

echo "🚀 เริ่ม RouterAI Proxy (port 8900)..."
python src/proxy.py --port 8900 &
PROXY_PID=$!

echo "📊 เริ่ม Dashboard (port 8899)..."
# Dashboard serves from same app on different port via uvicorn
sleep 1

echo ""
echo "✅ ระบบพร้อมใช้งาน!"
echo "📊 Dashboard: http://localhost:8899/dashboard/"
echo "🔀 API Proxy: http://localhost:8900"
echo ""
echo "📋 ขั้นตอนต่อไป:"
echo "   1. เปิด Dashboard"
echo "   2. ใส่ API Key (แนะนำ Groq)"
echo "   3. กด ⚡ เชื่อม OpenClaw"
echo "   4. รัน: openclaw restart"
echo ""

wait $PROXY_PID
EOF
chmod +x start.sh

# Also create CLI shortcut
cat > routerai << 'EOF'
#!/usr/bin/env bash
cd "$(dirname "$0")"
source venv/bin/activate
python src/cli.py "$@"
EOF
chmod +x routerai

# --- Done ---
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║${NC}  ✅ ติดตั้งสำเร็จ!                         ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}                                              ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  เริ่มใช้งาน:                                ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  ${CYAN}cd $INSTALL_DIR${NC}"
echo -e "${GREEN}║${NC}  ${CYAN}./start.sh${NC}"
echo -e "${GREEN}║${NC}                                              ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  📊 Dashboard: ${CYAN}http://localhost:8899/dashboard/${NC}"
echo -e "${GREEN}║${NC}  🔀 API Proxy: ${CYAN}http://localhost:8900${NC}"
echo -e "${GREEN}║${NC}                                              ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  CLI: ${CYAN}./routerai status${NC}                     ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  CLI: ${CYAN}./routerai setup${NC}                      ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  CLI: ${CYAN}./routerai doctor${NC}                     ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  CLI: ${CYAN}./routerai apply${NC}                      ${GREEN}║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo ""
