# 🇹🇭 OpenClaw Thai Dashboard + API Router

รวม API ฟรีจากหลายเจ้ามาไว้ที่เดียว — สลับอัตโนมัติเมื่อตัวไหนหมดโควต้า พร้อม Dashboard ภาษาไทยสำหรับจัดการ OpenClaw

## ✨ ฟีเจอร์

- 🔀 **Smart API Router** — รวม API ฟรี 10+ เจ้า สลับอัตโนมัติ
- 🇹🇭 **หน้าจอภาษาไทย** — UI ทั้งหมดเป็นภาษาไทย เข้าใจง่าย
- 📊 **Dashboard** — ดูสถานะ Bot, Model, Session, Token ทั้งหมด
- 💰 **ประหยัดเงิน** — Response Cache, Budget Control, Auto-downgrade
- 🔒 **ปลอดภัย** — รันบนเครื่องคุณ ไม่ส่งข้อมูลให้ใคร
- ⚡ **ติดตั้งง่าย** — คำสั่งเดียวจบ

## 🚀 ติดตั้ง (ต้องมี Python 3.8+)

```bash
curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/openclaw-thai-dashboard/main/scripts/install.sh | bash
```

หรือติดตั้งเอง:

```bash
git clone https://github.com/YOUR_USERNAME/openclaw-thai-dashboard.git
cd openclaw-thai-dashboard
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python src/main.py
```

## 📱 หน้าจอ

- **Dashboard**: http://localhost:8877
- **API Proxy**: http://localhost:8876

## 🔧 ตั้งค่า OpenClaw ให้ใช้ Router

Dashboard → แท็บ "เชื่อม OpenClaw" → กดปุ่ม ⚡

หรือแก้ `~/.openclaw/openclaw.json`:

```json
{
  "agents": {
    "defaults": {
      "model": {
        "primary": "groq/llama-3.3-70b-versatile",
        "fallbacks": ["gemini/gemini-2.0-flash", "openrouter/meta-llama/llama-3.1-70b-instruct:free"]
      }
    }
  }
}
```

## 📋 Provider ที่รองรับ

| Provider | ลิงก์สมัคร | ข้อดี |
|----------|------------|-------|
| ⚡ Groq | console.groq.com | เร็วสุด ~300ms |
| 🟢 Gemini | aistudio.google.com | ฟรี 15 RPM, vision |
| 🚀 Cerebras | cloud.cerebras.ai | เร็วมาก |
| 🌐 OpenRouter | openrouter.ai | โมเดลฟรีเยอะ |
| 🟣 Mistral | console.mistral.ai | Mistral models |
| 🔵 NVIDIA | build.nvidia.com | Llama ฟรี |
| 💎 DeepSeek | platform.deepseek.com | คุณภาพสูง |
| 🇨🇳 SiliconFlow | cloud.siliconflow.cn | Qwen ฟรี |
| 🤝 Together AI | api.together.xyz | $5 เครดิตฟรี |
| 🏠 Ollama | ollama.com | รัน Local ฟรี |

## 📄 License

MIT
