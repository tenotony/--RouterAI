# 🇹🇭 RouterAI + OpenClaw Thai Dashboard

รวม AI ฟรีจากหลายที่มาไว้ที่เดียว — สลับอัตโนมัติเมื่อตัวไหนหมดโควต้า พร้อม Dashboard ภาษาไทยสำหรับจัดการ OpenClaw

> Based on [RouterAI](https://github.com/tenotony/--RouterAI) + [OpenClaw-bot-review](https://github.com/xmanrui/OpenClaw-bot-review) — enhanced with Thai UI and OpenClaw integration

## ✨ ฟีเจอร์

- 🔀 **Smart API Router** — รวม API ฟรี 11 เจ้า สลับอัตโนมัติ
- 🇹🇭 **Dashboard ภาษาไทย** — หน้าจัดการสวยๆ เข้าใจง่าย
- ⚡ **OpenClaw Integration** — กดปุ่มเดียวเชื่อม OpenClaw
- 💾 **Response Cache** — ลด token consumption
- 🩺 **Doctor** — ตรวจสอบปัญหาระบบ
- 🔒 **ปลอดภัย** — รันบนเครื่องคุณ 100%
- 🛠️ **CLI** — จัดการผ่าน Terminal ภาษาไทย

## 🚀 ติดตั้ง

```bash
# One-line install
curl -fsSL https://raw.githubusercontent.com/tenotony/openclaw-thai-dashboard/main/scripts/install.sh | bash

# หรือ manual
git clone https://github.com/tenotony/openclaw-thai-dashboard.git
cd openclaw-thai-dashboard
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python src/proxy.py
```

## 📱 ใช้งาน

- **API Proxy**: http://localhost:8900 (OpenAI-compatible)
- **Dashboard**: http://localhost:8899/dashboard/
- **CLI**: `./routerai status`

### ขั้นตอน

1. เปิด Dashboard → แท็บ API Keys → ใส่ Key (แนะนำ Groq)
2. กด ⚡ "เชื่อม OpenClaw"
3. รัน `openclaw restart`

### CLI Commands

```bash
./routerai status    # 📊 แสดงสถานะระบบ
./routerai setup     # 🧙 ตัวช่วยตั้งค่า API Key
./routerai doctor    # 🩺 ตรวจสอบปัญหา
./routerai apply     # ⚡ ตั้งค่า OpenClaw อัตโนมัติ
./routerai provider list  # 🔌 แสดง Provider ทั้งหมด
./routerai provider free  # 🆓 แสดง Provider ฟรี
```

## 📋 Provider ที่รองรับ

| Provider | ข้อดี | Free Tier | สมัคร |
|----------|--------|-----------|-------|
| ⚡ Groq | เร็วสุด ~300ms | ฟรี 30 RPM | [console.groq.com](https://console.groq.com/keys) |
| 🧠 Xiaomi MiMo | คุณภาพสูง | ตามที่กำหนด | - |
| 🚀 Cerebras | เร็วมาก | ฟรี 30 RPM | [cloud.cerebras.ai](https://cloud.cerebras.ai) |
| 💎 DeepSeek | คุณภาพสูง | เครดิต $2 | [platform.deepseek.com](https://platform.deepseek.com) |
| 🟢 Gemini | Vision | ฟรี 15 RPM | [aistudio.google.com](https://aistudio.google.com/apikey) |
| 🌐 OpenRouter | โมเดลฟรีเยอะ | :free suffix | [openrouter.ai](https://openrouter.ai/settings/keys) |
| 🟣 Mistral | Mistral models | ทดลองฟรี | [console.mistral.ai](https://console.mistral.ai/api-keys) |
| 🔵 NVIDIA | Llama ฟรี | ฟรี 1000 req | [build.nvidia.com](https://build.nvidia.com) |
| 🇨🇳 SiliconFlow | Qwen ฟรี | ฟรีหลายโมเดล | [cloud.siliconflow.cn](https://cloud.siliconflow.cn) |
| 🤝 Together AI | $5 เครดิต | เครดิตฟรี | [api.together.xyz](https://api.together.xyz/settings/api-keys) |
| 🏠 Ollama | Local 100% ฟรี | ไม่จำกัด | [ollama.com](https://ollama.com) |

## 📁 โครงสร้าง

```
├── src/
│   ├── proxy.py       # FastAPI proxy + API endpoints (port 8900)
│   └── cli.py         # CLI tool ภาษาไทย
├── web/
│   └── index.html     # Dashboard UI
├── providers.json     # Provider configuration
├── scripts/
│   └── install.sh     # One-line installer
├── start.sh           # Start script (สร้างโดย installer)
├── routerai           # CLI shortcut (สร้างโดย installer)
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## 🏗️ Tech Stack

- **Backend**: FastAPI + Uvicorn + httpx (async)
- **Frontend**: Vanilla JS + CSS (ไม่ต้อง build)
- **Config**: JSON files (ไม่ต้อง database)
- **Fonts**: Sarabun + JetBrains Mono

## 📄 License

MIT
