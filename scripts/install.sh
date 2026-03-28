#!/bin/bash
# RouterAI - One-Line Installer
# curl -fsSL https://raw.githubusercontent.com/tenotony/RouterAI/main/scripts/install.sh | bash

set -e

echo ""
echo "╔══════════════════════════════════════╗"
echo "║     🔀 RouterAI Installer            ║"
echo "║     ติดตั้งอัตโนมัติ                  ║"
echo "╚══════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

REPO_URL="https://github.com/tenotony/RouterAI.git"
INSTALL_DIR="$HOME/RouterAI"

# Check and install Git
if ! command -v git &> /dev/null; then
    echo -e "${YELLOW}📦 กำลังติดตั้ง Git...${NC}"
    if command -v apt-get &> /dev/null; then
        sudo apt-get update && sudo apt-get install -y git
    elif command -v yum &> /dev/null; then
        sudo yum install -y git
    elif command -v brew &> /dev/null; then
        brew install git
    fi
fi

# Check and install Python 3
if ! command -v python3 &> /dev/null; then
    echo -e "${YELLOW}📦 กำลังติดตั้ง Python 3...${NC}"
    if command -v apt-get &> /dev/null; then
        sudo apt-get install -y python3 python3-pip python3-venv
    elif command -v yum &> /dev/null; then
        sudo yum install -y python3 python3-pip
    elif command -v brew &> /dev/null; then
        brew install python@3.12
    fi
fi

# Check and install pip
if ! python3 -m pip --version &> /dev/null 2>&1; then
    echo -e "${YELLOW}📦 กำลังติดตั้ง pip...${NC}"
    if command -v apt-get &> /dev/null; then
        sudo apt-get install -y python3-pip
    fi
fi

echo -e "${GREEN}✅ Git, Python, pip พร้อมแล้ว${NC}"

# Clone repo
if [ -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}📂 พบโฟลเดอร์เดิม กำลังอัปเดต...${NC}"
    cd "$INSTALL_DIR"
    git pull
else
    echo -e "${CYAN}📥 กำลังดาวน์โหลด RouterAI...${NC}"
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# Create virtual environment
echo -e "${CYAN}🐍 กำลังสร้าง Virtual Environment...${NC}"
python3 -m venv venv
source venv/bin/activate

# Install packages
echo -e "${CYAN}📦 กำลังติดตั้ง Python packages...${NC}"
pip install --upgrade pip 2>/dev/null || pip3 install --upgrade pip
pip install -r requirements.txt 2>/dev/null || pip3 install --break-system-packages -r requirements.txt

# Create default config if not exists
if [ ! -f "api_keys.json" ]; then
    echo "{}" > api_keys.json
    echo -e "${GREEN}✅ สร้าง api_keys.json แล้ว${NC}"
fi

echo ""
echo -e "${GREEN}╔══════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     ✅ ติดตั้งสำเร็จ!                ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}📋 ขั้นตอนต่อไป:${NC}"
echo ""
echo -e "  1. ตั้งค่า API Key:"
echo -e "     ${YELLOW}cd $INSTALL_DIR && source venv/bin/activate${NC}"
echo -e "     ${YELLOW}python routerai setup${NC}"
echo ""
echo -e "  2. เริ่มใช้งาน (Terminal 1 - Proxy):"
echo -e "     ${YELLOW}python src/proxy.py${NC}"
echo ""
echo -e "  3. เปิด Dashboard (Terminal 2):"
echo -e "     ${YELLOW}python src/dashboard.py${NC}"
echo ""
echo -e "  4. เปิด Browser ไปที่:"
echo -e "     ${YELLOW}http://127.0.0.1:8899${NC}"
echo ""
echo -e "  5. ตั้งค่า OpenClaw ให้ใช้ RouterAI:"
echo -e "     baseUrl: ${YELLOW}http://127.0.0.1:8900/v1${NC}"
echo ""
echo -e "${GREEN}💡 แนะนำ: สมัคร Groq ก่อน → console.groq.com/keys (เร็วสุด!)${NC}"
echo ""
