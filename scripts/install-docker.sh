#!/bin/bash
# RouterAI - One-Click Docker Installer (ภาษาไทย)
# curl -fsSL https://raw.githubusercontent.com/tenotony/RouterAI/main/scripts/install-docker.sh | bash

set -e

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   🔀 RouterAI - ติดตั้งด้วย Docker       ║"
echo "║   รวม AI ฟรีหลายเจ้าไว้ที่เดียว          ║"
echo "╚══════════════════════════════════════════╝"
echo ""

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

REPO_URL="https://github.com/tenotony/RouterAI.git"
INSTALL_DIR="$HOME/RouterAI"

# ─── Check Docker ─────────────────────────────────
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}📦 Docker ยังไม่ได้ติดตั้ง กำลังติดตั้ง...${NC}"
    if command -v apt-get &> /dev/null; then
        curl -fsSL https://get.docker.com | sudo bash
        sudo usermod -aG docker $USER
        echo -e "${GREEN}✅ ติดตั้ง Docker แล้ว (ต้อง logout/login เพื่อใช้ docker ไม่ต้อง sudo)${NC}"
    elif command -v yum &> /dev/null; then
        sudo yum install -y docker docker-compose-plugin
        sudo systemctl enable --now docker
    else
        echo -e "${RED}❌ ไม่สามารถติดตั้ง Docker อัตโนมัติได้ กรุณาติดตั้งเอง: https://docs.docker.com/get-docker/${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✅ Docker พร้อมใช้งาน${NC}"
fi

# Check docker compose
if ! docker compose version &> /dev/null; then
    echo -e "${YELLOW}📦 กำลังติดตั้ง Docker Compose plugin...${NC}"
    if command -v apt-get &> /dev/null; then
        sudo apt-get install -y docker-compose-plugin
    fi
fi

# ─── Clone or Update ─────────────────────────────
if [ -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}📂 พบโฟลเดอร์เดิม กำลังอัปเดต...${NC}"
    cd "$INSTALL_DIR"
    docker compose down 2>/dev/null || true
    git pull
else
    echo -e "${CYAN}📥 กำลังดาวน์โหลด RouterAI...${NC}"
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# ─── Create .env if not exists ───────────────────
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo -e "${GREEN}✅ สร้างไฟล์ .env แล้ว${NC}"
fi

# ─── Create api_keys.json if not exists ──────────
if [ ! -f "api_keys.json" ]; then
    echo '{}' > api_keys.json
    echo -e "${GREEN}✅ สร้าง api_keys.json แล้ว${NC}"
fi

# ─── Start Docker ────────────────────────────────
echo -e "${CYAN}🚀 กำลังเริ่มระบบ...${NC}"
docker compose up -d --build

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     ✅ ติดตั้งสำเร็จ!                    ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}📋 ขั้นตอนต่อไป:${NC}"
echo ""
echo -e "  1. ใส่ API Key ผ่าน Dashboard:"
echo -e "     เปิด Browser ไปที่: ${YELLOW}http://localhost:8899${NC}"
echo -e "     แล้วไปแท็บ '🔑 ใส่ API Key'"
echo ""
echo -e "  2. หรือแก้ไฟล์ .env โดยตรง:"
echo -e "     ${YELLOW}nano $INSTALL_DIR/.env${NC}"
echo -e "     แล้วรัน: ${YELLOW}cd $INSTALL_DIR && docker compose restart${NC}"
echo ""
echo -e "  3. เชื่อมต่อกับ OpenClaw:"
echo -e "     Dashboard → แท็บ '🔌 เชื่อม OpenClaw'"
echo -e "     กดปุ่ม '⚡ เชื่อมต่อ OpenClaw อัตโนมัติ'"
echo ""
echo -e "  4. ดูสถานะระบบ:"
echo -e "     ${YELLOW}docker compose logs -f${NC}"
echo ""
echo -e "${GREEN}💡 แนะนำ: สมัคร Groq ก่อน (เร็วสุด ฟรี) → ${YELLOW}console.groq.com/keys${NC}"
echo ""
echo -e "📊 Dashboard: ${YELLOW}http://localhost:8899${NC}"
echo -e "🔀 Proxy API: ${YELLOW}http://localhost:8900/v1${NC}"
echo ""
