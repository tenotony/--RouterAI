"""
RouterAI Dashboard Server
หน้าจัดการหลัก - รันที่ port 8899
Proxy API ไปที่ port 8900 (ใช้ PROXY_URL env สำหรับ Docker)
"""

import os
import sys
from pathlib import Path

# Ensure src/ is on the path
SRC_DIR = Path(__file__).parent
sys.path.insert(0, str(SRC_DIR))

from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Import shared components from proxy
from proxy import (
    router_ai,
    test_provider_connection,
    apply_openclaw_config,
    get_openclaw_config,
    OPENCLAW_CONFIG_PATH,
    PROVIDER_SIGNUP_LINKS,
    PROVIDER_DESCRIPTIONS,
    FREE_PROVIDERS,
    ProviderHealth,
)

# Proxy URL for Docker (default: same host)
PROXY_URL = os.environ.get("PROXY_URL", "http://127.0.0.1:8900")

dashboard_app = FastAPI(title="RouterAI Dashboard", version="1.2.0")

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
    return JSONResponse(content={"error": "Dashboard UI not found", "proxy_url": PROXY_URL})


@dashboard_app.get("/api/proxy-url")
async def get_proxy_url():
    """Return the proxy URL for the dashboard to use."""
    return {"proxy_url": PROXY_URL}


# ─── Re-export all proxy API endpoints ──────────────
# This makes the dashboard self-contained (can serve all APIs directly)

@dashboard_app.get("/api/status")
async def api_status():
    return router_ai.get_status()


@dashboard_app.get("/api/providers")
async def api_providers():
    return {"providers": router_ai.get_provider_details()}


@dashboard_app.post("/api/keys")
async def api_update_keys(request: Request):
    body = await request.json()
    updated = []
    for key, value in body.items():
        if key in router_ai.api_keys:
            router_ai.api_keys[key] = value.strip()
            updated.append(key)
    router_ai._save_keys()
    return {"success": True, "updated": updated, "message": f"บันทึก {len(updated)} key แล้ว"}


@dashboard_app.post("/api/test/{prov_id}")
async def api_test_provider(prov_id: str):
    if prov_id not in router_ai.providers:
        raise HTTPException(404, detail="ไม่พบ Provider นี้")
    prov_config = router_ai.providers[prov_id]
    env_key = prov_config.get("env_key", "")
    api_key = router_ai.api_keys.get(env_key, "") if env_key else ""
    result = await test_provider_connection(prov_id, prov_config, api_key)
    if result["success"]:
        router_ai.health[prov_id].record_success(result["latency_ms"] / 1000)
    else:
        router_ai.health[prov_id].record_failure(result["error"])
    return {"provider": prov_id, **result}


@dashboard_app.post("/api/test-all")
async def api_test_all():
    results = []
    for prov_id, prov_config in router_ai.providers.items():
        if not router_ai._is_provider_configured(prov_id):
            continue
        env_key = prov_config.get("env_key", "")
        api_key = router_ai.api_keys.get(env_key, "") if env_key else ""
        result = await test_provider_connection(prov_id, prov_config, api_key)
        if result["success"]:
            router_ai.health[prov_id].record_success(result["latency_ms"] / 1000)
        else:
            router_ai.health[prov_id].record_failure(result["error"])
        results.append({"provider": prov_id, **result})
    return {"results": results}


@dashboard_app.get("/api/doctor")
async def api_doctor():
    results = []
    for prov_id, prov in router_ai.providers.items():
        configured = router_ai._is_provider_configured(prov_id)
        health = router_ai.health.get(prov_id, ProviderHealth(name=prov_id))
        if not configured and prov.get("requires_key", True):
            results.append({"provider": prov_id, "name": prov["name"], "status": "warning", "message": "⚠️ ยังไม่ได้ใส่ API Key"})
        elif not health.is_healthy:
            results.append({"provider": prov_id, "name": prov["name"], "status": "error", "message": f"❌ {health.last_error}"})
        elif health.tested:
            results.append({"provider": prov_id, "name": prov["name"], "status": "ok", "message": f"✅ ใช้งานได้ (latency: {round(health.avg_latency*1000)}ms)"})
        else:
            results.append({"provider": prov_id, "name": prov["name"], "status": "ok", "message": "✅ ตั้งค่าแล้ว (ยังไม่ได้ทดสอบ)"})
    healthy_count = sum(1 for r in results if r["status"] == "ok")
    return {"status": "healthy" if healthy_count > 0 else "critical", "healthy_providers": healthy_count, "total_providers": len(results), "details": results}


@dashboard_app.post("/api/openclaw/apply")
async def api_apply_openclaw():
    try:
        result = apply_openclaw_config()
        return result
    except Exception as e:
        raise HTTPException(500, detail=f"ไม่สามารถตั้งค่า OpenClaw ได้: {str(e)}")


@dashboard_app.get("/api/openclaw/config")
async def api_get_openclaw_config():
    config = get_openclaw_config()
    return {"config_exists": OPENCLAW_CONFIG_PATH.exists(), "config_path": str(OPENCLAW_CONFIG_PATH), "config": config}


@dashboard_app.post("/api/budget")
async def api_budget(request: Request):
    body = await request.json()
    router_ai.budget_enabled = body.get("enabled", router_ai.budget_enabled)
    router_ai.daily_limit = body.get("daily_limit", router_ai.daily_limit)
    router_ai.monthly_limit = body.get("monthly_limit", router_ai.monthly_limit)
    return {"success": True, "budget": router_ai.get_status()["budget"]}


@dashboard_app.post("/api/cache/clear")
async def api_clear_cache():
    count = len(router_ai.response_cache)
    router_ai.response_cache.clear()
    return {"success": True, "cleared": count}


# Mount static files
if WEB_DIR.exists():
    dashboard_app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="RouterAI Dashboard")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8899)
    args = parser.parse_args()

    print(f"📊 Dashboard: http://{args.host}:{args.port}")
    print(f"🔀 Proxy:     {PROXY_URL}")
    uvicorn.run(dashboard_app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
