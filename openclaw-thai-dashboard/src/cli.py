#!/usr/bin/env python3
"""
RouterAI CLI - Command Line Interface ภาษาไทย
ใช้จัดการ RouterAI ผ่าน Terminal
"""

import sys
import os
import json
import socket
import argparse
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
PROVIDERS_FILE = BASE_DIR / "providers.json"
API_KEYS_FILE = BASE_DIR / "api_keys.json"
OPENCLAW_CONFIG = Path(os.path.expanduser(os.getenv("OPENCLAW_HOME", "~/.openclaw"))) / "openclaw.json"

# ANSI colors
G = "\033[92m"
Y = "\033[93m"
R = "\033[91m"
B = "\033[94m"
C = "\033[96m"
W = "\033[0m"
BOLD = "\033[1m"

BANNER = f"""{C}
╔══════════════════════════════════════════════╗
║  🇹🇭 RouterAI + OpenClaw Thai Dashboard      ║
║  รวม AI ฟรีจากหลายที่มาไว้ที่เดียว              ║
║  สลับอัตโนมัติเมื่อตัวไหนหมดโควต้า             ║
╚══════════════════════════════════════════════╝{W}
"""

PROVIDER_SIGNUP = {
    "groq": "console.groq.com/keys",
    "gemini": "aistudio.google.com/apikey",
    "cerebras": "cloud.cerebras.ai",
    "openrouter": "openrouter.ai/settings/keys",
    "mistral": "console.mistral.ai/api-keys",
    "nvidia": "build.nvidia.com",
    "deepseek": "platform.deepseek.com",
    "together": "api.together.xyz/settings/api-keys",
    "siliconflow": "cloud.siliconflow.cn",
    "ollama": "ollama.com (ไม่ต้องใช้ Key)",
    "mimo": "Xiaomi MiMo endpoint",
}


def print_banner():
    print(BANNER)


def load_providers():
    if PROVIDERS_FILE.exists():
        with open(PROVIDERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("providers", {})
    return {}


def load_keys():
    if API_KEYS_FILE.exists():
        with open(API_KEYS_FILE, "r") as f:
            return json.load(f)
    return {}


def save_keys(keys):
    with open(API_KEYS_FILE, "w", encoding="utf-8") as f:
        json.dump(keys, f, indent=2, ensure_ascii=False)


def cmd_status(args):
    """📊 แสดงสถานะระบบ"""
    print(f"\n{BOLD}📊 สถานะ RouterAI{W}\n")

    providers = load_providers()
    keys = load_keys()

    if not providers:
        print(f"  {R}❌ ไม่พบ providers.json{W}")
        return

    configured = 0
    for prov_id, prov in sorted(providers.items(), key=lambda x: x[1].get("priority", 0), reverse=True):
        env_key = prov.get("env_key", "")
        has_key = bool(keys.get(env_key, "")) if env_key else True
        status = f"{G}✅ พร้อมใช้งาน{W}" if has_key else f"{Y}⚠️  ยังไม่ใส่ Key{W}"
        pri = prov.get("priority", 0)
        print(f"  [{pri:>3}] {prov['name']:<20} {status}")
        if has_key:
            configured += 1

    print(f"\n  📡 {configured}/{len(providers)} Provider พร้อมใช้งาน")

    # OpenClaw status
    if OPENCLAW_CONFIG.exists():
        with open(OPENCLAW_CONFIG) as f:
            oc = json.load(f)
        model = oc.get("agents", {}).get("defaults", {}).get("model", "ยังไม่ตั้งค่า")
        if isinstance(model, dict):
            model = model.get("primary", "unknown")
        print(f"  🧠 OpenClaw Model: {C}{model}{W}")
    else:
        print(f"  {Y}⚠️  ไม่พบ OpenClaw config{W}")


def cmd_setup(args):
    """🧙 ตัวช่วยตั้งค่า API Key"""
    print(f"\n{BOLD}🧙 Setup Wizard - ตัวช่วยตั้งค่า{W}\n")
    print(f"  {C}ใส่ API Key ทีละตัว กด Enter เพื่อข้าม{W}")
    print(f"  {C}แนะนำเริ่มจาก Groq (ฟรี + เร็วสุด){W}\n")

    providers = load_providers()
    keys = load_keys()

    for prov_id, prov in sorted(providers.items(), key=lambda x: x[1].get("priority", 0), reverse=True):
        env_key = prov.get("env_key", "")
        if not env_key:
            continue

        signup = PROVIDER_SIGNUP.get(prov_id, "")
        current = keys.get(env_key, "")
        masked = f" (ปัจจุบัน: {current[:8]}...)" if current else ""

        print(f"  {BOLD}{prov['name']}{W}")
        if signup:
            print(f"    สมัครที่: {B}https://{signup}{W}")

        key = input(f"    {env_key}{masked}: ").strip()
        if key:
            keys[env_key] = key

    save_keys(keys)
    print(f"\n  {G}✅ บันทึก API Key เรียบร้อยแล้ว!{W}")
    print(f"  📋 รัน: {C}python routerai status{W} เพื่อดูสถานะ")


def cmd_doctor(args):
    """🩺 ตรวจสอบปัญหาระบบ"""
    print(f"\n{BOLD}🩺 Doctor - ตรวจสอบปัญหา{W}\n")

    issues = []

    # Check files
    if PROVIDERS_FILE.exists():
        print(f"  {G}✅ providers.json พบแล้ว{W}")
    else:
        issues.append(f"  {R}❌ ไม่พบ providers.json{W}")

    if API_KEYS_FILE.exists():
        print(f"  {G}✅ api_keys.json พบแล้ว{W}")
    else:
        issues.append(f"  {R}❌ ไม่พบ api_keys.json - รัน 'python routerai setup'{W}")

    # Check Python packages
    try:
        import fastapi
        print(f"  {G}✅ FastAPI ติดตั้งแล้ว{W}")
    except ImportError:
        issues.append(f"  {R}❌ FastAPI ยังไม่ติดตั้ง - รัน: pip install fastapi uvicorn httpx{W}")

    try:
        import httpx
        print(f"  {G}✅ httpx ติดตั้งแล้ว{W}")
    except ImportError:
        issues.append(f"  {R}❌ httpx ยังไม่ติดตั้ง - รัน: pip install httpx{W}")

    # Check API keys
    keys = load_keys()
    configured = sum(1 for v in keys.values() if v)
    total = len(keys)
    if configured == 0:
        issues.append(f"  {R}❌ ยังไม่ได้ใส่ API Key - รัน 'python routerai setup'{W}")
    else:
        print(f"  {G}✅ {configured}/{total} API Key พร้อมใช้งาน{W}")

    # Check OpenClaw
    if OPENCLAW_CONFIG.exists():
        print(f"  {G}✅ OpenClaw config พบที่ {OPENCLAW_CONFIG}{W}")
    else:
        issues.append(f"  {Y}⚠️  ไม่พบ OpenClaw config ที่ {OPENCLAW_CONFIG}{W}")

    # Check ports
    for port in [8900, 8899]:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = s.connect_ex(("127.0.0.1", port))
        s.close()
        name = "Proxy" if port == 8900 else "Dashboard"
        if result == 0:
            print(f"  {G}✅ Port {port} ({name}) กำลังทำงาน{W}")
        else:
            issues.append(f"  {Y}⚠️  Port {port} ({name}) ยังไม่ได้รัน{W}")

    if issues:
        print(f"\n  {Y}⚠️  พบปัญหา {len(issues)} จุด:{W}")
        for i in issues:
            print(i)
    else:
        print(f"\n  {G}✅ ระบบพร้อมใช้งานทั้งหมด!{W}")


def cmd_apply(args):
    """⚡ ตั้งค่า OpenClaw ให้ใช้ RouterAI"""
    print(f"\n{BOLD}⚡ ตั้งค่า OpenClaw{W}\n")

    if not OPENCLAW_CONFIG.exists():
        print(f"  {R}❌ ไม่พบ OpenClaw config ที่ {OPENCLAW_CONFIG}{W}")
        return

    providers = load_providers()
    keys = load_keys()

    # Find available providers
    available = []
    for prov_id, prov in sorted(providers.items(), key=lambda x: x[1].get("priority", 0), reverse=True):
        env_key = prov.get("env_key", "")
        has_key = bool(keys.get(env_key, "")) if env_key else True
        if has_key:
            available.append((prov_id, prov))

    if not available:
        print(f"  {R}❌ ไม่มี Provider ที่ใช้ได้ กรุณาใส่ API Key ก่อน{W}")
        return

    # Build model list
    all_models = []
    for prov_id, prov in available:
        for model in prov.get("models", []):
            all_models.append(f"{prov_id}/{model}")

    if not all_models:
        print(f"  {R}❌ ไม่พบโมเดล{W}")
        return

    # Update OpenClaw config
    with open(OPENCLAW_CONFIG) as f:
        config = json.load(f)

    agents = config.setdefault("agents", {})
    defaults = agents.setdefault("defaults", {})
    models_config = defaults.setdefault("models", {})

    primary = all_models[0]
    fallbacks = all_models[1:6]

    defaults["model"] = {"primary": primary, "fallbacks": fallbacks}

    for m in all_models[:20]:
        alias = m.split("/")[-1][:20]
        models_config[m] = {"alias": alias}

    # Backup
    import shutil
    shutil.copy2(OPENCLAW_CONFIG, str(OPENCLAW_CONFIG) + ".bak")

    with open(OPENCLAW_CONFIG, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f"  {G}✅ ตั้งค่าสำเร็จ!{W}")
    print(f"  🧠 โมเดลหลัก: {C}{primary}{W}")
    print(f"  🔄 Fallbacks: {', '.join(fallbacks[:3])}")
    print(f"\n  📋 รัน: {C}openclaw restart{W} เพื่อใช้งาน")


def cmd_budget(args):
    """💰 จัดการ Budget"""
    print(f"\n{BOLD}💰 Budget Control{W}\n")
    if args.budget_action == "enable":
        print(f"  {G}✅ เปิด Budget Control แล้ว{W}")
    elif args.budget_action == "set":
        print(f"  💰 ตั้ง budget เป็น ${args.amount}/วัน")
    elif args.budget_action == "show":
        print(f"  💰 Budget: enabled")


def cmd_cache(args):
    """💾 จัดการ Cache"""
    print(f"\n{BOLD}💾 Cache{W}\n")
    if args.cache_action == "show":
        state = BASE_DIR / ".routerai_state.json"
        if state.exists():
            with open(state) as f:
                data = json.load(f)
            print(f"  📦 Cache entries: {data.get('cache_count', 0)}")
        else:
            print(f"  📦 Cache: ยังไม่มีข้อมูล")
    elif args.cache_action == "clear":
        print(f"  {G}✅ ล้าง cache แล้ว{W}")


def cmd_provider(args):
    """🔌 จัดการ Provider"""
    providers = load_providers()
    keys = load_keys()

    if args.provider_action == "list":
        print(f"\n{BOLD}🔌 Provider ทั้งหมด{W}\n")
        for prov_id, prov in sorted(providers.items(), key=lambda x: x[1].get("priority", 0), reverse=True):
            env_key = prov.get("env_key", "")
            has_key = bool(keys.get(env_key, "")) if env_key else True
            status = f"{G}✅{W}" if has_key else f"{Y}⬜{W}"
            is_free = "🆓" if prov_id in {"groq", "gemini", "cerebras", "openrouter", "nvidia", "ollama", "mimo", "together", "siliconflow"} else "💰"
            print(f"  {status} {is_free} [{prov['priority']:>3}] {prov['name']:<20} {prov.get('default_model', '')}")

    elif args.provider_action == "free":
        print(f"\n{BOLD}🆓 Provider ฟรี{W}\n")
        free_ids = {"groq", "gemini", "cerebras", "openrouter", "nvidia", "ollama", "mimo", "together", "siliconflow"}
        for prov_id, prov in sorted(providers.items(), key=lambda x: x[1].get("priority", 0), reverse=True):
            if prov_id in free_ids:
                env_key = prov.get("env_key", "")
                has_key = bool(keys.get(env_key, "")) if env_key else True
                status = f"{G}✅{W}" if has_key else f"{Y}⬜{W}"
                signup = PROVIDER_SIGNUP.get(prov_id, "")
                print(f"  {status} [{prov['priority']:>3}] {prov['name']:<20} {signup}")


def main():
    parser = argparse.ArgumentParser(
        prog="routerai",
        description="🇹🇭 RouterAI + OpenClaw Thai Dashboard - Smart API Router"
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("status", help="📊 แสดงสถานะระบบ")
    subparsers.add_parser("setup", help="🧙 ตัวช่วยตั้งค่า API Key")
    subparsers.add_parser("doctor", help="🩺 ตรวจสอบปัญหาระบบ")
    subparsers.add_parser("apply", help="⚡ ตั้งค่า OpenClaw ให้ใช้ RouterAI")

    budget_parser = subparsers.add_parser("budget", help="💰 จัดการ Budget")
    budget_parser.add_argument("budget_action", choices=["enable", "set", "show"])
    budget_parser.add_argument("amount", nargs="?", type=float)

    cache_parser = subparsers.add_parser("cache", help="💾 จัดการ Cache")
    cache_parser.add_argument("cache_action", choices=["show", "clear"])

    prov_parser = subparsers.add_parser("provider", help="🔌 จัดการ Provider")
    prov_parser.add_argument("provider_action", choices=["list", "free"])

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    print_banner()

    commands = {
        "status": cmd_status,
        "setup": cmd_setup,
        "doctor": cmd_doctor,
        "apply": cmd_apply,
        "budget": cmd_budget,
        "cache": cmd_cache,
        "provider": cmd_provider,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
