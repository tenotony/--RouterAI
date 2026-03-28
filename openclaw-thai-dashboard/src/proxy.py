#!/usr/bin/env python3
"""
RouterAI + OpenClaw Thai Dashboard - Smart API Router
รวม AI ฟรีจากหลายที่มาไว้ที่เดียว สลับอัตโนมัติเมื่อตัวไหนหมดโควต้า
OpenAI-compatible API proxy - ใช้แทน OpenAI endpoint ได้เลย
"""

import os
import json
import time
import logging
import hashlib
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import httpx
import uvicorn
from dotenv import load_dotenv

# ─── Config Paths ───────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env")

PROVIDERS_FILE = BASE_DIR / "providers.json"
API_KEYS_FILE = BASE_DIR / "api_keys.json"
STATE_FILE = BASE_DIR / ".routerai_state.json"
LOG_FILE = BASE_DIR / "routerai.log"
OPENCLAW_CONFIG = Path(os.path.expanduser(os.getenv("OPENCLAW_HOME", "~/.openclaw"))) / "openclaw.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("routerai")


# ─── Provider Health Tracker ────────────────────────────────────

@dataclass
class ProviderHealth:
    name: str
    is_healthy: bool = True
    last_error: Optional[str] = None
    last_error_time: float = 0
    consecutive_failures: int = 0
    total_requests: int = 0
    total_failures: int = 0
    avg_latency: float = 0
    _latency_sum: float = 0
    _latency_count: int = 0
    tested: bool = False

    def record_success(self, latency: float):
        self.total_requests += 1
        self.consecutive_failures = 0
        self.is_healthy = True
        self.tested = True
        self._latency_sum += latency
        self._latency_count += 1
        self.avg_latency = self._latency_sum / self._latency_count

    def record_failure(self, error: str):
        self.total_requests += 1
        self.total_failures += 1
        self.consecutive_failures += 1
        self.last_error = error
        self.last_error_time = time.time()
        self.tested = True
        if self.consecutive_failures >= 3:
            self.is_healthy = False

    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 1.0
        return 1 - (self.total_failures / self.total_requests)


# ─── Constants ──────────────────────────────────────────────────

FREE_PROVIDERS = {"groq", "gemini", "cerebras", "openrouter", "nvidia", "ollama", "mimo", "together", "siliconflow"}
PAID_PROVIDERS = {"deepseek", "mistral"}

PROVIDER_SIGNUP_LINKS = {
    "groq": "https://console.groq.com/keys",
    "gemini": "https://aistudio.google.com/apikey",
    "cerebras": "https://cloud.cerebras.ai",
    "openrouter": "https://openrouter.ai/settings/keys",
    "mistral": "https://console.mistral.ai/api-keys",
    "nvidia": "https://build.nvidia.com/explore/discover",
    "deepseek": "https://platform.deepseek.com",
    "together": "https://api.together.xyz/settings/api-keys",
    "siliconflow": "https://cloud.siliconflow.cn",
    "ollama": "https://ollama.com",
    "mimo": "https://your-mimo-endpoint.com",
}

PROVIDER_DESCRIPTIONS = {
    "groq": {"th": "⚡ เร็วสุด ~300ms | ฟรี 30 RPM", "free_tier": "ฟรี 30 RPM, Llama/Mixtral"},
    "gemini": {"th": "👁️ รองรับ Vision | ฟรี 15 RPM", "free_tier": "ฟรี 15 RPM, Vision"},
    "cerebras": {"th": "🚀 เร็วมาก 30 RPM | ฟรี", "free_tier": "ฟรี 30 RPM, Llama"},
    "openrouter": {"th": "🌐 โมเดลฟรีเยอะ | :free suffix", "free_tier": "ฟรีหลายโมเดล (ลงท้าย :free)"},
    "mistral": {"th": "🟣 Mistral models | ทดลองฟรี", "free_tier": "ทดลองฟรี จำกัด"},
    "nvidia": {"th": "🔵 Llama ฟรี | NIM Platform", "free_tier": "ฟรี 1000 req, Llama"},
    "deepseek": {"th": "💎 คุณภาพสูง | ราคาถูก", "free_tier": "เครดิตฟรีเริ่มต้น $2"},
    "together": {"th": "🤝 หลายโมเดล | $5 เครดิตฟรี", "free_tier": "เครดิตฟรี $5"},
    "siliconflow": {"th": "🇨🇳 Qwen/DeepSeek ฟรี", "free_tier": "ฟรีหลายโมเดล"},
    "ollama": {"th": "🏠 รันบนเครื่องตัวเอง 100% ฟรี", "free_tier": "ฟรีไม่จำกัด (ต้องมี GPU)"},
    "mimo": {"th": "🧠 Xiaomi MiMo | คุณภาพสูง", "free_tier": "ตามที่ Xiaomi กำหนด"},
}


# ─── Core Router ────────────────────────────────────────────────

class RouterAI:
    def __init__(self):
        self.providers: Dict[str, dict] = {}
        self.api_keys: Dict[str, str] = {}
        self.health: Dict[str, ProviderHealth] = {}
        self.response_cache: Dict[str, dict] = {}
        self.cache_ttl = 3600
        self.budget_enabled = False
        self.daily_limit = 0.0
        self.monthly_limit = 0.0
        self.daily_spent = 0.0
        self.monthly_spent = 0.0
        self.total_requests = 0
        self.total_tokens = 0
        self.start_time = time.time()
        self.load_config()

    def load_config(self):
        """Load providers, API keys from JSON files."""
        if PROVIDERS_FILE.exists():
            with open(PROVIDERS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.providers = data.get("providers", {})
        else:
            self._create_default_providers()

        if API_KEYS_FILE.exists():
            with open(API_KEYS_FILE, "r", encoding="utf-8") as f:
                self.api_keys = json.load(f)
        else:
            self._create_default_keys()

        # Also load from environment variables
        for prov_id, prov in self.providers.items():
            env_key = prov.get("env_key", "")
            if env_key and env_key in os.environ:
                val = os.environ[env_key]
                if val:
                    self.api_keys[env_key] = val

        # Init health trackers
        for prov_id in self.providers:
            if prov_id not in self.health:
                self.health[prov_id] = ProviderHealth(name=prov_id)

        logger.info(f"Loaded {len(self.providers)} providers, {sum(1 for v in self.api_keys.values() if v)} keys configured")

    def _create_default_providers(self):
        if PROVIDERS_FILE.exists():
            with open(PROVIDERS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.providers = data.get("providers", {})

    def _create_default_keys(self):
        keys = {}
        for prov in self.providers.values():
            env_key = prov.get("env_key", "")
            if env_key:
                keys[env_key] = ""
        with open(API_KEYS_FILE, "w", encoding="utf-8") as f:
            json.dump(keys, f, indent=2)
        self.api_keys = keys

    def _save_keys(self):
        with open(API_KEYS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.api_keys, f, indent=2, ensure_ascii=False)

    def _is_provider_configured(self, prov_id: str) -> bool:
        prov = self.providers.get(prov_id, {})
        env_key = prov.get("env_key", "")
        if not env_key:  # No key needed (ollama)
            return True
        return bool(self.api_keys.get(env_key, ""))

    def get_available_providers(self) -> List[tuple]:
        available = []
        for prov_id, prov in sorted(self.providers.items(), key=lambda x: x[1].get("priority", 0), reverse=True):
            if self._is_provider_configured(prov_id):
                h = self.health.get(prov_id, ProviderHealth(name=prov_id))
                if h.is_healthy:
                    available.append((prov_id, prov))
        return available

    def select_provider(self, model_name: Optional[str] = None, prefer_free: bool = True) -> Optional[tuple]:
        available = self.get_available_providers()
        if not available:
            return None

        if model_name:
            for prov_id, prov in available:
                if model_name in prov.get("models", []):
                    return (prov_id, prov, model_name)

        # Pick highest priority available
        prov_id, prov = available[0]
        return (prov_id, prov, prov.get("default_model", prov.get("models", [""])[0]))

    def get_provider_details(self) -> Dict[str, Any]:
        details = {}
        for prov_id, prov in self.providers.items():
            h = self.health.get(prov_id, ProviderHealth(name=prov_id))
            details[prov_id] = {
                "name": prov["name"],
                "api_base": prov.get("api_base", ""),
                "env_key": prov.get("env_key", ""),
                "models": prov.get("models", []),
                "default_model": prov.get("default_model", ""),
                "priority": prov.get("priority", 0),
                "max_tokens": prov.get("max_tokens", 4096),
                "supports_vision": prov.get("supports_vision", False),
                "requires_key": prov.get("requires_key", True),
                "configured": self._is_provider_configured(prov_id),
                "healthy": h.is_healthy,
                "tested": h.tested,
                "total_requests": h.total_requests,
                "total_failures": h.total_failures,
                "success_rate": round(h.success_rate * 100, 1),
                "avg_latency_ms": round(h.avg_latency * 1000) if h.avg_latency else 0,
                "last_error": h.last_error,
                "is_free": prov_id in FREE_PROVIDERS,
                "signup_link": PROVIDER_SIGNUP_LINKS.get(prov_id, ""),
                "description_th": PROVIDER_DESCRIPTIONS.get(prov_id, {}).get("th", ""),
                "free_tier": PROVIDER_DESCRIPTIONS.get(prov_id, {}).get("free_tier", ""),
            }
        return details

    def get_status(self) -> Dict[str, Any]:
        configured = sum(1 for pid in self.providers if self._is_provider_configured(pid))
        healthy = sum(1 for pid in self.providers if self.health.get(pid, ProviderHealth(name=pid)).is_healthy and self._is_provider_configured(pid))
        return {
            "uptime_seconds": round(time.time() - self.start_time),
            "total_providers": len(self.providers),
            "configured_providers": configured,
            "healthy_providers": healthy,
            "total_requests": self.total_requests,
            "total_tokens": self.total_tokens,
            "cache_size": len(self.response_cache),
            "budget": {
                "enabled": self.budget_enabled,
                "daily_limit": self.daily_limit,
                "daily_spent": self.daily_spent,
                "monthly_limit": self.monthly_limit,
                "monthly_spent": self.monthly_spent,
            },
        }


# ─── Global RouterAI instance ───────────────────────────────────
router_ai = RouterAI()


# ─── OpenClaw Config Helpers ─────────────────────────────────────

def get_openclaw_config() -> dict:
    if OPENCLAW_CONFIG.exists():
        with open(OPENCLAW_CONFIG, "r") as f:
            return json.load(f)
    return {}


def apply_openclaw_config() -> dict:
    """Configure OpenClaw to use RouterAI as its LLM provider."""
    config = get_openclaw_config()
    if not config:
        return {"success": False, "error": "ไม่พบ OpenClaw config กรุณาติดตั้ง OpenClaw ก่อน"}

    available = router_ai.get_available_providers()
    if not available:
        return {"success": False, "error": "ไม่มี Provider ที่ใช้ได้ กรุณาใส่ API Key อย่างน้อย 1 ตัว"}

    agents = config.setdefault("agents", {})
    defaults = agents.setdefault("defaults", {})
    models = defaults.setdefault("models", {})

    # Build model list from all available providers
    all_models = []
    for prov_id, prov in available:
        for model in prov.get("models", []):
            full = f"{prov_id}/{model}"
            all_models.append(full)
            models[full] = {"alias": model.split("/")[-1][:20]}

    if not all_models:
        return {"success": False, "error": "ไม่พบโมเดลที่ใช้ได้"}

    primary = all_models[0]
    fallbacks = all_models[1:6]

    defaults["model"] = {
        "primary": primary,
        "fallbacks": fallbacks,
    }

    # Backup
    if OPENCLAW_CONFIG.exists():
        shutil.copy2(OPENCLAW_CONFIG, str(OPENCLAW_CONFIG) + ".bak")

    with open(OPENCLAW_CONFIG, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    return {
        "success": True,
        "primary": primary,
        "fallbacks": fallbacks,
        "total_models": len(all_models),
        "message": f"✅ ตั้งค่า OpenClaw สำเร็จ! โมเดลหลัก: {primary}",
    }


# ─── Test Provider Connection ───────────────────────────────────

async def test_provider_connection(prov_id: str, prov_config: dict, api_key: str) -> dict:
    """Test connection to a provider."""
    base_url = prov_config.get("api_base", "")
    model = prov_config.get("default_model", prov_config.get("models", ["test"])[0])
    requires_key = prov_config.get("requires_key", True)

    if requires_key and not api_key:
        return {"success": False, "error": "ยังไม่ได้ใส่ API Key", "latency_ms": 0}

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        start = time.time()
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": "Say hi"}],
                    "max_tokens": 5,
                },
            )
        latency = (time.time() - start) * 1000

        if resp.status_code == 200:
            return {"success": True, "latency_ms": round(latency), "model": model}
        else:
            return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text[:200]}", "latency_ms": round(latency)}

    except Exception as e:
        return {"success": False, "error": str(e), "latency_ms": 0}


# ─── FastAPI App ────────────────────────────────────────────────

app = FastAPI(title="RouterAI + OpenClaw Thai Dashboard", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

WEB_DIR = BASE_DIR / "web"


# ─── OpenAI-compatible endpoints ────────────────────────────────

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """OpenAI-compatible chat completions with smart routing."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, detail="Invalid JSON")

    messages = body.get("messages", [])
    model_name = body.get("model", "")
    stream = body.get("stream", False)

    # Parse provider/model
    target_provider = None
    target_model = model_name
    if "/" in model_name:
        parts = model_name.split("/", 1)
        if parts[0] in router_ai.providers:
            target_provider = parts[0]
            target_model = parts[1]

    # Cache check
    cache_key = hashlib.md5(json.dumps({"m": messages, "m2": model_name}, sort_keys=True).encode()).hexdigest()
    if cache_key in router_ai.response_cache:
        cached = router_ai.response_cache[cache_key]
        if time.time() - cached.get("ts", 0) < router_ai.cache_ttl:
            logger.info(f"📦 Cache HIT: {model_name}")
            if stream:
                return _stream_cached_response(cached["data"])
            return JSONResponse(content=cached["data"])

    # Select provider
    if target_provider:
        prov_config = router_ai.providers.get(target_provider)
        if not prov_config:
            raise HTTPException(404, detail=f"ไม่พบ Provider: {target_provider}")
    else:
        selected = router_ai.select_provider(target_model, prefer_free=True)
        if not selected:
            raise HTTPException(503, detail="ไม่มี Provider ที่ใช้ได้ กรุณาใส่ API Key")
        target_provider, prov_config, target_model = selected

    return await _forward_request(target_provider, prov_config, target_model, body, messages, stream, cache_key)


@app.get("/v1/models")
async def list_models():
    """List all available models."""
    models = []
    for prov_id, prov in router_ai.providers.items():
        if router_ai._is_provider_configured(prov_id):
            for m in prov.get("models", []):
                models.append({
                    "id": f"{prov_id}/{m}",
                    "object": "model",
                    "owned_by": prov_id,
                })
    return {"object": "list", "data": models}


# ─── Dashboard API endpoints ────────────────────────────────────

@app.get("/api/status")
async def api_status():
    return router_ai.get_status()


@app.get("/api/providers")
async def api_providers():
    return {"providers": router_ai.get_provider_details()}


@app.post("/api/keys")
async def api_update_keys(request: Request):
    body = await request.json()
    updated = []
    for key, value in body.items():
        if key in router_ai.api_keys:
            router_ai.api_keys[key] = value.strip()
            updated.append(key)
    router_ai._save_keys()
    return {"success": True, "updated": updated, "message": f"บันทึก {len(updated)} key แล้ว"}


@app.post("/api/test/{prov_id}")
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


@app.post("/api/test-all")
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


@app.get("/api/doctor")
async def api_doctor():
    results = []
    for prov_id, prov in router_ai.providers.items():
        configured = router_ai._is_provider_configured(prov_id)
        h = router_ai.health.get(prov_id, ProviderHealth(name=prov_id))
        if not configured and prov.get("requires_key", True):
            results.append({"provider": prov_id, "name": prov["name"], "status": "warning", "message": "⚠️ ยังไม่ได้ใส่ API Key"})
        elif not h.is_healthy:
            results.append({"provider": prov_id, "name": prov["name"], "status": "error", "message": f"❌ {h.last_error}"})
        elif h.tested:
            results.append({"provider": prov_id, "name": prov["name"], "status": "ok", "message": f"✅ ใช้งานได้ (latency: {round(h.avg_latency*1000)}ms)"})
        else:
            results.append({"provider": prov_id, "name": prov["name"], "status": "ok", "message": "✅ ตั้งค่าแล้ว (ยังไม่ได้ทดสอบ)"})
    healthy_count = sum(1 for r in results if r["status"] == "ok")
    return {"status": "healthy" if healthy_count > 0 else "critical", "healthy_providers": healthy_count, "total_providers": len(results), "details": results}


@app.post("/api/openclaw/apply")
async def api_apply_openclaw():
    try:
        result = apply_openclaw_config()
        return result
    except Exception as e:
        raise HTTPException(500, detail=f"ไม่สามารถตั้งค่า OpenClaw ได้: {str(e)}")


@app.get("/api/openclaw/config")
async def api_get_openclaw_config():
    config = get_openclaw_config()
    return {"config_exists": OPENCLAW_CONFIG.exists(), "config_path": str(OPENCLAW_CONFIG), "config": config}


@app.post("/api/budget")
async def api_budget(request: Request):
    body = await request.json()
    router_ai.budget_enabled = body.get("enabled", router_ai.budget_enabled)
    router_ai.daily_limit = body.get("daily_limit", router_ai.daily_limit)
    router_ai.monthly_limit = body.get("monthly_limit", router_ai.monthly_limit)
    return {"success": True, "budget": router_ai.get_status()["budget"]}


@app.post("/api/cache/clear")
async def api_clear_cache():
    count = len(router_ai.response_cache)
    router_ai.response_cache.clear()
    return {"success": True, "cleared": count}


# ─── Dashboard UI ───────────────────────────────────────────────

@app.get("/")
async def home():
    index = WEB_DIR / "index.html"
    if index.exists():
        return JSONResponse(
            content={"message": "Open Dashboard at /dashboard"},
            headers={"Location": "/dashboard"},
            status_code=302,
        )
    return JSONResponse(content={"error": "Dashboard UI not found"})


# Mount static files
if WEB_DIR.exists():
    app.mount("/dashboard", StaticFiles(directory=str(WEB_DIR), html=True), name="dashboard")


# ─── Helper functions ───────────────────────────────────────────

async def _forward_request(prov_id, prov_config, model_name, body, messages, stream, cache_key):
    """Forward request to provider with retry + failover."""
    base_url = prov_config.get("api_base", "")
    env_key = prov_config.get("env_key", "")
    api_key = router_ai.api_keys.get(env_key, "") if env_key else ""

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    forward_body = dict(body)
    forward_body["model"] = model_name

    max_retries = 3
    timeout = 60

    for attempt in range(max_retries):
        try:
            start = time.time()

            if stream:
                return await _stream_forward(base_url, headers, forward_body, timeout, prov_id)

            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(
                    f"{base_url}/chat/completions",
                    headers=headers,
                    json=forward_body,
                )

            latency = (time.time() - start) * 1000

            if resp.status_code == 200:
                router_ai.health[prov_id].record_success(latency / 1000)
                router_ai.total_requests += 1
                result = resp.json()

                # Cache
                router_ai.response_cache[cache_key] = {"data": result, "ts": time.time()}

                logger.info(f"✅ {prov_id}/{model_name} - {round(latency)}ms")
                return JSONResponse(content=result)

            elif resp.status_code == 429:
                router_ai.health[prov_id].record_failure("rate_limited")
                logger.warning(f"⚠️ {prov_id} rate limited")
                continue
            else:
                router_ai.health[prov_id].record_failure(f"HTTP {resp.status_code}")
                # Try failover
                if attempt < max_retries - 1:
                    selected = router_ai.select_provider(None, prefer_free=True)
                    if selected and selected[0] != prov_id:
                        prov_id, prov_config, model_name = selected
                        base_url = prov_config.get("api_base", "")
                        env_key = prov_config.get("env_key", "")
                        api_key = router_ai.api_keys.get(env_key, "") if env_key else ""
                        headers = {"Content-Type": "application/json"}
                        if api_key:
                            headers["Authorization"] = f"Bearer {api_key}"
                        forward_body["model"] = model_name
                        continue
                raise HTTPException(resp.status_code, detail=f"Provider error: {resp.text[:200]}")

        except httpx.TimeoutException:
            router_ai.health[prov_id].record_failure("timeout")
            if attempt < max_retries - 1:
                continue
            raise HTTPException(504, detail="Request timeout")

        except Exception as e:
            router_ai.health[prov_id].record_failure(str(e))
            if attempt < max_retries - 1:
                continue
            raise HTTPException(502, detail=str(e))

    raise HTTPException(503, detail="All providers failed")


async def _stream_forward(base_url, headers, body, timeout, prov_id):
    """Stream response from provider."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream("POST", f"{base_url}/chat/completions", headers=headers, json=body) as resp:
                if resp.status_code != 200:
                    router_ai.health[prov_id].record_failure(f"HTTP {resp.status_code}")
                    raise HTTPException(resp.status_code, detail="Provider error")

                async def generate():
                    start = time.time()
                    async for line in resp.aiter_lines():
                        if line:
                            yield line + "\n\n"
                    latency = (time.time() - start) * 1000
                    router_ai.health[prov_id].record_success(latency / 1000)
                    router_ai.total_requests += 1

                return StreamingResponse(generate(), media_type="text/event-stream")

    except Exception as e:
        router_ai.health[prov_id].record_failure(str(e))
        raise HTTPException(502, detail=str(e))


def _stream_cached_response(cached):
    """Stream a cached response."""
    import uuid

    async def generate():
        choice = cached.get("choices", [{}])[0]
        content = choice.get("message", {}).get("content", "")
        chunk = {
            "id": f"cached-{uuid.uuid4().hex[:8]}",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "choices": [{"delta": {"content": content}, "index": 0, "finish_reason": "stop"}],
        }
        yield f"data: {json.dumps(chunk)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


# ─── Main ───────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="RouterAI + OpenClaw Thai Dashboard")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8900)
    parser.add_argument("--proxy-only", action="store_true", help="Run proxy only (no dashboard)")
    args = parser.parse_args()

    print(f"""
╔══════════════════════════════════════════════╗
║  🇹🇭 RouterAI + OpenClaw Thai Dashboard      ║
║                                              ║
║  🔀 API Proxy:    http://{args.host}:{args.port:<17}║
║  📊 Dashboard:    http://{args.host}:8899         ║
║                                              ║
║  กด Ctrl+C เพื่อหยุด                          ║
╚══════════════════════════════════════════════╝
    """)

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
