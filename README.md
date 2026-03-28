# RouterAI - Smart API Router for OpenClaw

รวม AI ฟรีจากหลายที่มาไว้ที่เดียว สลับอัตโนมัติเมื่อตัวไหนหมดโควต้า

OpenAI-compatible API proxy ใช้แทน OpenAI endpoint ได้เลย สำหรับ OpenClaw, ChatGPT-like apps, หรือโปรแกรมอะไรก็ได้ที่รองรับ OpenAI API

## ⚡ ติดตั้งภายใน 1 นาที

### วิธีที่ 1: One-Line Install (แนะนำ)

```bash
curl -fsSL https://raw.githubusercontent.com/tenotony/RouterAI/main/scripts/install.sh | bash
```

สคริปต์จะ:
- ✅ ตรวจสอบและติดตั้ง Git, Python, pip อัตโนมัติ (ถ้ายังไม่มี)
- ✅ ดาวน์โหลดโค้ด
- ✅ สร้าง Virtual Environment
- ✅ ติดตั้ง Python packages
- ✅ สร้าง config files

### วิธีที่ 2: Windows

ดาวน์โหลดไฟล์ [setup.bat](scripts/setup.bat) แล้วดับเบิลคลิก

ต้องมี Python 3.10+ ติดตั้งก่อน → [ดาวน์โหลดที่นี่](https://www.python.org/downloads/)

### วิธีที่ 3: Docker

```bash
git clone https://github.com/tenotony/RouterAI.git
cd RouterAI
docker compose up -d
```

## 🚀 เริ่มใช้งาน

```bash
cd RouterAI
source venv/bin/activate

# ดูสถานะระบบ
python routerai status

# ตัวช่วยตั้งค่า (Interactive Wizard)
python routerai setup

# ตรวจสอบปัญหา
python routerai doctor

# จัดการ Budget
python routerai budget enable    # เปิด Budget
python routerai budget set 5.00  # จำกัด $5/วัน
python routerai budget show      # ดูสถานะ

# จัดการ Cache
python routerai cache show       # ดูสถิติ
python routerai cache clear      # ล้าง cache
```

## 🏃‍♂️ รัน RouterAI

```bash
cd RouterAI
source venv/bin/activate

# Terminal 1: รัน Proxy (API ที่ port 8900)
python src/proxy.py

# Terminal 2: รัน Dashboard (หน้าจัดการที่ port 8899)
python src/dashboard.py
```

Dashboard: http://127.0.0.1:8899

## 🔌 เชื่อมต่อกับ OpenClaw

### วิธีที่ 1: ผ่าน Setup Wizard (แนะนำ)
```bash
python routerai setup
```

### วิธีที่ 2: แก้เอง

แก้ `~/.openclaw/openclaw.json`:

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
| ⚡ Groq | [console.groq.com/keys](https://console.groq.com/keys) | เร็วสุดๆ ~300ms | ⭐⭐⭐⭐⭐ |
| 🟢 Google Gemini | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | ฟรี 15 RPM, vision | ⭐⭐⭐⭐ |
| 🚀 Cerebras | [cloud.cerebras.ai](https://cloud.cerebras.ai) | เร็วมาก | ⭐⭐⭐⭐⭐ |
| 🌐 OpenRouter | [openrouter.ai/settings/keys](https://openrouter.ai/settings/keys) | โมเดลฟรีเยอะ | ⭐⭐⭐ |
| 🟣 Mistral | [console.mistral.ai](https://console.mistral.ai/api-keys/) | Mistral models | ⭐⭐⭐ |
| 🔵 NVIDIA | [build.nvidia.com](https://build.nvidia.com/explore/discover) | Llama ฟรี | ⭐⭐⭐ |
| 💎 DeepSeek | [platform.deepseek.com](https://platform.deepseek.com) | คุณภาพสูง | ⭐⭐⭐⭐ |
| 🇨🇳 SiliconFlow | [cloud.siliconflow.cn](https://cloud.siliconflow.cn) | Qwen ฟรี | ⭐⭐⭐ |
| 🤖 Ollama | [ollama.com](https://ollama.com) | รัน Local ฟรี | ⭐⭐⭐⭐ |

**💡 แนะนำ: สมัครแค่ Groq ตัวเดียวก็เริ่มใช้ได้เลย!**

## 🔑 ใส่ API Key

ใส่ Key ได้ 3 ทาง:

1. **Setup Wizard** → `python routerai setup` (แนะนำ!)
2. **Dashboard** → http://127.0.0.1:8899 → แท็บ "ใส่ API Key"
3. **แก้ไฟล์** → เปิด `api_keys.json` แล้วใส่:
```json
{
  "GROQ_API_KEY": "gsk_xxxxx",
  "GOOGLE_API_KEY": "AIzaSyxxxxx",
  "CEREBRAS_API_KEY": "csk-xxxxx"
}
```

## 💰 Budget Control

จำกัดค่าใช้จ่ายไม่ให้บานปลาย:

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

## 🏗️ โครงสร้าง

```
RouterAI/
├── src/
│   ├── proxy.py           # Main proxy server (OpenAI-compatible)
│   ├── dashboard.py       # Web dashboard
│   └── cli.py             # CLI commands
├── web/
│   └── index.html         # Dashboard UI (ภาษาไทย)
├── scripts/
│   ├── install.sh         # One-line installer
│   └── setup.bat          # Windows setup
├── routerai               # CLI shortcut
├── docker-compose.yml
├── Dockerfile
├── providers.json         # Provider config
├── api_keys.json          # API keys (เก็บเฉพาะเครื่อง)
├── requirements.txt
└── README.md
```

## 🔄 ระบบทำงานยังไง

```
Request → RouterAI Proxy (port 8900)
 │
 ├─ 1) Response Cache Check
 │    └─ HIT → return cached response (ไม่เสียตังค์!)
 │
 ├─ 2) Budget Check
 │    └─ EXCEEDED → downgrade model / block
 │
 ├─ 3) Smart Routing Engine
 │    ├─ Latency scoring
 │    ├─ Error tracking
 │    └─ Auto-failover
 │
 ├─ 4) Provider Pool
 │    ├─ Groq (priority: 100)
 │    ├─ MiMo (priority: 98)
 │    ├─ Cerebras (priority: 95)
 │    ├─ Gemini (priority: 88)
 │    ├─ OpenRouter (priority: 85)
 │    └─ ...more providers
 │
 └─ 5) Response → Cache it → Track cost → Return to Client
```

## 🔒 ความปลอดภัย

- ✅ รันบนเครื่องคุณ ไม่ส่งข้อมูลให้ใคร
- ✅ ไม่มี tracking / analytics
- ✅ API Key เก็บเฉพาะเครื่องคุณ
- ✅ โค้ดเปิดทั้งหมด (MIT License)

## 🤝 มีส่วนร่วม

- 🐛 พบบั๊ก → [เปิด Issue](https://github.com/tenotony/RouterAI/issues)
- 💡 มีไอเดีย → [Pull Request](https://github.com/tenotony/RouterAI/pulls)

## 📄 License

MIT — ใช้ฟรี แก้ไขได้ แจกต่อได้
