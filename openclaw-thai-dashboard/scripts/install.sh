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

REPO_URL="https://github.com/YOUR_USERNAME/openclaw-thai-dashboard.git"
INSTALL_DIR="$HOME/openclaw-thai-dashboard"

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║${NC}  🇹🇭 ${GREEN}OpenClaw Thai Dashboard + API Router${NC}    ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}     ติดตั้งระบบจัดการ OpenClaw ภาษาไทย        ${CYAN}║${NC}"
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

PY_VERSION=$($PYTHON -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "${GREEN}✅ Python $PY_VERSION${NC}"

# --- Check Git ---
echo -e "${YELLOW}[2/5] ตรวจสอบ Git...${NC}"
if ! command -v git &>/dev/null; then
    echo -e "${YELLOW}⚠️ ไม่พบ Git กำลังติดตั้ง...${NC}"
    if command -v apt &>/dev/null; then
        sudo apt install -y git
    elif command -v yum &>/dev/null; then
        sudo yum install -y git
    elif command -v brew &>/dev/null; then
        brew install git
    else
        echo -e "${RED}❌ กรุณาติดตั้ง Git ด้วยตนเอง${NC}"
        exit 1
    fi
fi
echo -e "${GREEN}✅ Git พร้อม${NC}"

# --- Download ---
echo -e "${YELLOW}[3/5] ดาวน์โหลดโค้ด...${NC}"
if [ -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}⚠️ พบโฟลเดอร์เดิม กำลังอัปเดต...${NC}"
    cd "$INSTALL_DIR"
    git pull origin main 2>/dev/null || true
else
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi
echo -e "${GREEN}✅ ดาวน์โหลดสำเร็จ${NC}"

# --- Setup venv + install ---
echo -e "${YELLOW}[4/5] ติดตั้ง dependencies...${NC}"
$PYTHON -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo -e "${GREEN}✅ ติดตั้งสำเร็จ${NC}"

# --- Setup config ---
echo -e "${YELLOW}[5/5] ตั้งค่าเริ่มต้น...${NC}"
if [ ! -f config/.env ]; then
    cp config/.env.example config/.env
    echo -e "${GREEN}✅ สร้างไฟล์ .env${NC}"
else
    echo -e "${GREEN}✅ มีไฟล์ .env แล้ว${NC}"
fi

# --- Create start script ---
cat > start.sh << 'EOF'
#!/usr/bin/env bash
cd "$(dirname "$0")"
source venv/bin/activate
python src/main.py
EOF
chmod +x start.sh

# --- Done ---
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║${NC}  ✅ ติดตั้งสำเร็จ!                         ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}                                              ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  เริ่มใช้งาน:                                ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  ${CYAN}cd $INSTALL_DIR${NC}"
echo -e "${GREEN}║${NC}  ${CYAN}./start.sh${NC}"
echo -e "${GREEN}║${NC}                                              ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  📊 Dashboard: ${CYAN}http://localhost:8877${NC}      ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  🔀 API Proxy: ${CYAN}http://localhost:8876${NC}      ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}                                              ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  📝 ขั้นตอนต่อไป:                            ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  1. เปิด Dashboard                           ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  2. ไปหน้า API Keys → ใส่ Key (แนะนำ Groq)  ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  3. กดปุ่ม ⚡ เชื่อม OpenClaw                 ${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  4. รัน: openclaw restart                    ${GREEN}║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo ""
