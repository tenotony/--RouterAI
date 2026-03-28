# 🔀 RouterAI

**รวม AI ฟรีจากหลายที่มาไว้ที่เดียว** — สลับอัตโนมัติเมื่อตัวไหนหมดโควต้า

OpenAI-compatible API proxy ใช้แทน OpenAI endpoint ได้เลย สำหรับ OpenClaw, ChatGPT-like apps, หรือโปรแกรมอะไรก็ได้ที่รองรับ OpenAI API

---

## 🚀 ติดตั้งด้วย Docker (แนะนำ!)

```bash
curl -fsSL https://raw.githubusercontent.com/tenotony/RouterAI/main/scripts/install-docker.sh | bash
```

สคริปต์จะ:
- ✅ ตรวจสอบและติดตั้ง Docker อัตโนมัติ (ถ้ายังไม่มี)
- ✅ ดาวน์โหลดโค้ด
- ✅ สร้างไฟล์ตั้งค่า
- ✅ เริ่มระบบด้วย Docker Compose

## 🪟 Windows

```bash
git clone https://github.com/tenotony/RouterAI.git
cd RouterAI
docker compose up -d
```

ต้องมี Docker Desktop ติดตั้งก่อน → [ดาวน์โหลดที่นี่](https://www.docker.com/products/docker-desktop/)

## 🐧 Linux / macOS (ไม่ใช้ Docker)

```bash
git clone https://github.com/tenotony/RouterAI.git
cd RouterAI
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

```bash
# Terminal 1: รัน Proxy (API ที่ port 8900)
python src/proxy.py

# Terminal 2: รัน Dashboard (หน้าจัดการที่ port 8899)
python src/dashboard.py
```

Dashboard: [http://127.0.0.1:8899](http://127.0.0.1:8899)

## 📊 หน้า Dashboard

เปิด [http://localhost:8899](http://localhost:8899) หลังติดตั้งเสร็จ:

| แท็บ | หน้าที่ |
|------|---------|
| 🔧 **Provider** | ดูสถานะทุก Provider ที่มี |
| 🔑 **ใส่ API Key** | กรอก Key สำหรับแต่ละเจ้า |
| 🔌 **เชื่อม OpenClaw** | ตั้งค่า OpenClaw อัตโนมัติ |
| 🩺 **ตรวจสอบ** | วิเคราะห์ปัญหาในระบบ |

## 🔌 เชื่อมต่อกับ OpenClaw

1. ใส่ API Key อย่างน้อย 1 ตัว (แนะนำ Groq)
2. Dashboard → แท็บ "เชื่อม OpenClaw" → กดปุ่ม ⚡
3. รัน `openclaw restart`

หรือแก้ไข `~/.openclaw/openclaw.json` เอง:

```json
{
  "llm": {
    "provider": "openai",
    "baseUrl": "http://127.0.0.1:8900/v1",
    "apiKey": "routerai",
    "model": "groq/llama-3.3-70b-versatile"
  }
}
```

## 📡 Provider ที่รองรับ

| Provider | ลิงก์สมัคร | ทำไมต้องสมัคร | ความเร็ว |
|----------|-----------|--------------|---------|
| ⚡ **Groq** | [console.groq.com/keys](https://console.groq.com/keys) | เร็วสุดๆ ~300ms | ⭐⭐⭐⭐⭐ |
| 🟢 **Google Gemini** | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | ฟรี 15 RPM, vision | ⭐⭐⭐⭐ |
| 🚀 **Cerebras** | [cloud.cerebras.ai](https://cloud.cerebras.ai) | เร็วมาก | ⭐⭐⭐⭐⭐ |
| 🌐 **OpenRouter** | [openrouter.ai/settings/keys](https://openrouter.ai/settings/keys) | โมเดลฟรีเยอะ | ⭐⭐⭐ |
| 🟣 **Mistral** | [console.mistral.ai](https://console.mistral.ai/api-keys/) | Mistral models | ⭐⭐⭐ |
| 🔵 **NVIDIA** | [build.nvidia.com](https://build.nvidia.com/explore/discover) | Llama ฟรี | ⭐⭐⭐ |
| 💎 **DeepSeek** | [platform.deepseek.com](https://platform.deepseek.com) | คุณภาพสูง | ⭐⭐⭐⭐ |
| 🇨🇳 **SiliconFlow** | [cloud.siliconflow.cn](https://cloud.siliconflow.cn) | Qwen ฟรี | ⭐⭐⭐ |
| 🤝 **Together AI** | [api.together.xyz](https://api.together.xyz/settings/api-keys) | $5 เครดิตฟรี | ⭐⭐⭐ |
| 🏠 **Ollama** | [ollama.com](https://ollama.com) | รัน Local ฟรี | ⭐⭐⭐⭐ |

> 💡 **แนะนำ**: สมัครแค่ **Groq** ตัวเดียวก็เริ่มใช้ได้เลย!

## 🔑 ใส่ API Key

ใส่ Key ได้ 3 ทาง:

1. **Dashboard** (แนะนำ!) → http://localhost:8899 → แท็บ "ใส่ API Key"
2. **แก้ไฟล์ .env** → เปิด `.env` แล้วใส่:
   ```env
   GROQ_API_KEY=gsk_xxxxx
   GOOGLE_API_KEY=AIzaSyxxxxx
   CEREBRAS_API_KEY=csk-xxxxx
   ```
3. **ไฟล์ api_keys.json** → เปิดแล้วใส่:
   ```json
   {
     "GROQ_API_KEY": "gsk_xxxxx",
     "GOOGLE_API_KEY": "AIzaSyxxxxx",
     "CEREBRAS_API_KEY": "csk-xxxxx"
   }
   ```

## 💰 จำกัดค่าใช้จ่าย (Budget)

```bash
# เปิดใช้งาน
python routerai budget enable

# จำกัด $5/วัน
python routerai budget set 5.00

# ดูสถานะ
python routerai budget show
```

เมื่อถึงขีดจำกัด:
- **downgrade** (default) → สลับไป model ที่ถูกกว่าอัตโนมัติ
- **block** → หยุดรับ request
- **warn** → แค่เตือน

## 🏗️ โครงสร้างโปรเจค

```
RouterAI/
├── src/
│   ├── proxy.py           # Main proxy server (OpenAI-compatible)
│   ├── dashboard.py       # Web dashboard server
│   └── cli.py             # CLI commands
├── web/
│   └── index.html         # Dashboard UI (ภาษาไทย)
├── scripts/
│   ├── install.sh          # One-line installer (venv)
│   ├── install-docker.sh   # One-line installer (Docker)
│   └── setup.bat           # Windows setup
├── routerai                # CLI shortcut
├── docker-compose.yml
├── Dockerfile
├── .env.example            # Environment template
├── providers.json          # Provider config
├── requirements.txt
└── README.md
```

## ⚙️ หลักการทำงาน

```
Request → RouterAI Proxy (port 8900)
 │
 ├─ 1) Response Cache Check
 │   └─ HIT → return cached response (ไม่เสียตังค์!)
 │
 ├─ 2) Budget Check
 │   └─ EXCEEDED → downgrade model / block
 │
 ├─ 3) Smart Routing Engine
 │   ├─ Latency scoring
 │   ├─ Error tracking
 │   └─ Auto-failover
 │
 ├─ 4) Provider Pool
 │   ├─ Groq (priority: 100)
 │   ├─ Cerebras (priority: 95)
 │   ├─ DeepSeek (priority: 90)
 │   ├─ Gemini (priority: 88)
 │   ├─ OpenRouter (priority: 85)
 │   └─ ...more providers
 │
 └─ 5) Response → Cache it → Track cost → Return to Client
```

## 🔒 ความปลอดภัย

- ✅ รันบนเครื่องคุณ ไม่ส่งข้อมูลให้ใคร
- ✅ ไม่มี tracking / analytics
- ✅ API Key เก็บเฉพาะเครื่องคุณ
- ✅ โค้ดเปิดทั้งหมด (MIT License)

## 🐛 ปัญหาที่พบบ่อย

| ปัญหา | วิธีแก้ |
|-------|--------|
| Docker ไม่เริ่ม | ตรวจสอบ Docker ติดตั้งแล้ว: `docker --version` |
| Port ถูกใช้ | เปลี่ยน port ใน `docker-compose.yml` |
| API Key ไม่ทำงาน | กด "ทดสอบ" ใน Dashboard เพื่อเช็ค |
| OpenClaw เชื่อมไม่ได้ | รัน `openclaw restart` หลังตั้งค่า |

## 🐛 พบบั๊ก?

- [เปิด Issue](https://github.com/tenotony/RouterAI/issues)
- [เข้ากลุ่ม Facebook](https://www.facebook.com/groups/1248346110734837)

---

**License**: MIT
