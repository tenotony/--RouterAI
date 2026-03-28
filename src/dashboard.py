"""
RouterAI Dashboard Server
หน้าจัดการหลัก - รันที่ port 8899
Proxy API ไปที่ port 8900
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from proxy import app as proxy_app, router_ai, test_provider_connection, apply_openclaw_config, get_openclaw_config, OPENCLAW_CONFIG_PATH

dashboard_app = FastAPI(title="RouterAI Dashboard")

dashboard_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

WEB_DIR = Path(__file__).parent.parent / "web"


@dashboard_app.get("/")
async def home():
    index = WEB_DIR / "index.html"
    if index.exists():
        return FileResponse(str(index), media_type="text/html")
    return {"error": "Dashboard UI not found"}


# Mount all proxy API endpoints onto dashboard too (so dashboard is self-contained)
dashboard_app.include_router(proxy_app.router)


if WEB_DIR.exists():
    dashboard_app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="RouterAI Dashboard")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8899)
    args = parser.parse_args()

    print(f"📊 Dashboard: http://{args.host}:{args.port}")
    print(f"🔀 Proxy:     http://{args.host}:8900")
    uvicorn.run(dashboard_app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
