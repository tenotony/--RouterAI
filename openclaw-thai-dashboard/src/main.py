#!/usr/bin/env python3
"""
OpenClaw Thai Dashboard + API Router
Main entry point - starts both proxy server and dashboard
"""

import os
import sys
import json
import signal
import threading
import logging
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / "config" / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("openclaw-thai")

def check_dependencies():
    """Check required packages are installed"""
    required = ["flask", "flask_cors", "requests", "dotenv", "cachetools", "psutil"]
    missing = []
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"❌ ขาดแพ็กเกจ: {', '.join(missing)}")
        print("รัน: pip install -r requirements.txt")
        sys.exit(1)

def start_proxy():
    """Start the API proxy server"""
    from proxy import create_proxy_app
    port = int(os.getenv("PROXY_PORT", "8876"))
    app = create_proxy_app()
    logger.info(f"🔀 API Proxy เริ่มทำงานที่ port {port}")
    app.run(host="0.0.0.0", port=port, threaded=True, use_reloader=False)

def start_dashboard():
    """Start the web dashboard"""
    from dashboard import create_dashboard_app
    port = int(os.getenv("DASHBOARD_PORT", "8877"))
    app = create_dashboard_app()
    logger.info(f"📊 Dashboard เริ่มทำงานที่ port {port}")
    app.run(host="0.0.0.0", port=port, threaded=True, use_reloader=False)

def main():
    check_dependencies()

    print("""
╔══════════════════════════════════════════════╗
║   🇹🇭 OpenClaw Thai Dashboard + API Router   ║
║                                              ║
║   📊 Dashboard: http://localhost:8877        ║
║   🔀 API Proxy: http://localhost:8876        ║
║                                              ║
║   กด Ctrl+C เพื่อหยุดการทำงาน               ║
╚══════════════════════════════════════════════╝
    """)

    # Start proxy in background thread
    proxy_thread = threading.Thread(target=start_proxy, daemon=True)
    proxy_thread.start()

    # Start dashboard in main thread
    try:
        start_dashboard()
    except KeyboardInterrupt:
        logger.info("👋 กำลังปิดระบบ...")
        sys.exit(0)

if __name__ == "__main__":
    main()
