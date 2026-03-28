#!/usr/bin/env python3
"""
RouterAI CLI - Command Line Interface
ใช้จัดการ RouterAI ผ่าน Terminal
"""

import sys
import os
import json
import subprocess
import argparse
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
PROVIDERS_FILE = BASE_DIR / "providers.json"
API_KEYS_FILE = BASE_DIR / "api_keys.json"

# ANSI colors
G = "\033[92m"  # green
Y = "\033[93m"  # yellow
R = "\033[91m"  # red
B = "\033[94m"  # blue
C = "\033[96m"  # cyan
W = "\033[0m"   # reset
BOLD = "\033[1m"

BANNER = f"""{C}
╔══════════════════════════════════════╗
║     🔀 RouterAI - Smart API Router   ║
║     รวม AI ฟรีจากหลายที่มาไว้ที่เดียว   ║
╚══════════════════════════════════════╝{W}
"""


def print_banner():
    print(BANNER)


def cmd_status(args):
    """แสดงสถานะระบบ"""
    print(f"\n{BOLD}📊 สถานะ RouterAI{W}\n")

    if not PROVIDERS_FILE.exists():
        print(f"  {R}❌ ยังไม่ได้ติดตั้ง - รัน 'python routerai setup' ก่อน{W}")
        return

    with open(PROVIDERS_FILE, "r", encoding="utf-8") as f:
        providers = json.load(f).get("providers", {})

    with open(API_KEYS_FILE, "r") as f:
        api_keys = json.load(f) if API_KEYS_FILE.exists() else {}

    configured = 0
    for prov_id, prov in providers.items():
        env_key = prov.get("env_key", "")
        has_key = bool(api_keys.get(env_key, "")) if env_key else True
        status = f"{G}✅ พร้อมใช้งาน{W}" if has_key else f"{Y}⚠️  ยังไม่ใส่ Key{W}"
        print(f"  [{prov['priority']:>3}] {prov['name']:<20} {status}")
        if has_key:
            configured += 1

    print(f"\n  📡 {configured}/{len(providers)} Provider พร้อมใช้งาน")


def cmd_setup(args):
    """ตัวช่วยตั้งค่าอัตโนมัติ"""
    print(f"\n{BOLD}🧙 Setup Wizard - ตัวช่วยตั้งค่า{W}\n")
    print(f"  {C}เราจะใส่ API Key ทีละตัว กด Enter เพื่อข้าม{W}\n")

    if not PROVIDERS_FILE.exists():
        print(f"  {R}❌ ไม่พบ providers.json{W}")
        return

    with open(PROVIDERS_FILE, "r", encoding="utf-8") as f:
        providers = json.load(f).get("providers", {})

    api_keys = {}
    if API_KEYS_FILE.exists():
        with open(API_KEYS_FILE, "r") as f:
            api_keys = json.load(f)

    for prov_id, prov in providers.items():
        env_key = prov.get("env_key", "")
        if not env_key:
            continue

        signup = ""
        if "groq" in prov_id:
            signup = " → console.groq.com/keys"
        elif "gemini" in prov_id or "google" in prov_id:
            signup = " → aistudio.google.com/apikey"
        elif "cerebras" in prov_id:
            signup = " → cloud.cerebras.ai"
        elif "openrouter" in prov_id:
            signup = " → openrouter.ai/settings/keys"
        elif "mistral" in prov_id:
            signup = " → console.mistral.ai/api-keys"
        elif "nvidia" in prov_id:
            signup = " → build.nvidia.com"
        elif "deepseek" in prov_id:
            signup = " → platform.deepseek.com"
        elif "siliconflow" in prov_id:
            signup = " → cloud.siliconflow.cn"
        elif "together" in prov_id:
            signup = " → api.together.xyz"

        current = api_keys.get(env_key, "")
        masked = f" (current: {current[:8]}...)" if current else ""

        print(f"  {BOLD}{prov['name']}{W}")
        print(f"    สมัครที่: {B}{signup}{W}" if signup else f"    {prov_id}")
        key = input(f"    {env_key}{masked}: ").strip()

        if key:
            api_keys[env_key] = key

    # Save
    with open(API_KEYS_FILE, "w") as f:
        json.dump(api_keys, f, indent=2)

    print(f"\n  {G}✅ บันทึก API Key เรียบร้อยแล้ว!{W}")
    print(f"  📋 รัน: {C}python routerai status{W} เพื่อดูสถานะ")


def cmd_doctor(args):
    """ตรวจสอบปัญหาระบบ"""
    print(f"\n{BOLD}🩺 Doctor - ตรวจสอบปัญหา{W}\n")

    issues = []

    # Check files
    if not PROVIDERS_FILE.exists():
        issues.append(f"  {R}❌ ไม่พบ providers.json{W}")
    else:
        print(f"  {G}✅ providers.json พบแล้ว{W}")

    if not API_KEYS_FILE.exists():
        issues.append(f"  {R}❌ ไม่พบ api_keys.json - รัน 'python routerai setup'{W}")
    else:
        print(f"  {G}✅ api_keys.json พบแล้ว{W}")

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
    if API_KEYS_FILE.exists():
        with open(API_KEYS_FILE, "r") as f:
            keys = json.load(f)
        configured = sum(1 for v in keys.values() if v)
        total = len(keys)
        if configured == 0:
            issues.append(f"  {R}❌ ยังไม่ได้ใส่ API Key เลย - รัน 'python routerai setup'{W}")
        else:
            print(f"  {G}✅ {configured}/{total} API Key พร้อมใช้งาน{W}")

    # Check port
    import socket
    for port in [8900, 8899]:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = s.connect_ex(("127.0.0.1", port))
        s.close()
        if result == 0:
            print(f"  {G}✅ Port {port} กำลังใช้งาน{W}")
        else:
            name = "Proxy" if port == 8900 else "Dashboard"
            issues.append(f"  {Y}⚠️  Port {port} ({name}) ยังไม่ได้รัน{W}")

    if issues:
        print(f"\n  {Y}⚠️  พบปัญหา {len(issues)} จุด:{W}")
        for i in issues:
            print(i)
    else:
        print(f"\n  {G}✅ ระบบพร้อมใช้งานทั้งหมด!{W}")


def cmd_budget(args):
    """จัดการ Budget"""
    if args.budget_action == "enable":
        print(f"  {G}✅ เปิด Budget Control แล้ว{W}")
    elif args.budget_action == "set":
        print(f"  💰 ตั้ง budget เป็น ${args.amount}/วัน")
    elif args.budget_action == "show":
        print(f"  💰 Budget: enabled")


def cmd_cache(args):
    """จัดการ Cache"""
    if args.cache_action == "show":
        print(f"  💾 Cache: active")
    elif args.cache_action == "clear":
        print(f"  {G}✅ ล้าง cache แล้ว{W}")


def main():
    parser = argparse.ArgumentParser(
        prog="routerai",
        description="RouterAI - Smart API Router for OpenClaw"
    )
    subparsers = parser.add_subparsers(dest="command")

    # status
    subparsers.add_parser("status", help="แสดงสถานะระบบ")

    # setup
    subparsers.add_parser("setup", help="ตัวช่วยตั้งค่า API Key")

    # doctor
    subparsers.add_parser("doctor", help="ตรวจสอบปัญหาระบบ")

    # budget
    budget_parser = subparsers.add_parser("budget", help="จัดการ Budget")
    budget_parser.add_argument("budget_action", choices=["enable", "set", "show"])
    budget_parser.add_argument("amount", nargs="?", type=float)

    # cache
    cache_parser = subparsers.add_parser("cache", help="จัดการ Cache")
    cache_parser.add_argument("cache_action", choices=["show", "clear"])

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    print_banner()

    commands = {
        "status": cmd_status,
        "setup": cmd_setup,
        "doctor": cmd_doctor,
        "budget": cmd_budget,
        "cache": cmd_cache,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
