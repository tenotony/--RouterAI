"""
RouterAI - Smart API Router for OpenClaw
รวม AI ฟรีจากหลายที่มาไว้ที่เดียว สลับอัตโนมัติเมื่อตัวไหนหมดโควต้า
OpenAI-compatible API proxy - ใช้แทน OpenAI endpoint ได้เลย
"""

import os
import json
import time
import asyncio
import logging
import hashlib
import secrets
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import httpx
import uvicorn

# ─── Config Paths ───────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent
PROVIDERS_FILE = BASE_DIR / "providers.json"
API_KEYS_FILE = BASE_DIR / "api_keys.json"
STATE_FILE = BASE_DIR / ".routerai_state.json"
LOG_FILE = BASE_DIR / "routerai.log"

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
    tested: bool = False  # Has this provider been tested?

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


# ─── Core Router ────────────────────────────────────────────────

# Free vs Paid provider classification
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
    "mimo": {"th": "🧠 Xiaomi MiMo | ภาษาไทยดี", "free_tier": "ตามที่ Xiaomi กำหนด"},
}


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
        """Load providers, API keys, and state from JSON files."""
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

        # Init health trackers (preserve existing state)
        for prov_id in self.providers:
            if prov_id not in self.health:
                self.health[prov_id] = ProviderHealth(name=prov_id)

        logger.info(f"Loaded {len(self.providers)} providers, {sum(1 for v in self.api_keys.values() if v)} keys configured")

    def _create_default_providers(self):
        self.providers = {
            "groq": {
                "name": "Groq",
                "api_base": "https://api.groq.com/openai/v1",
                "env_key": "GROQ_API_KEY",
                "models": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"],
                "default_model": "llama-3.3-70b-versatile",
                "priority": 100,
                "max_tokens": 8192,
                "supports_vision": False,
            },
            "mimo": {
                "name": "Xiaomi MiMo",
                "api_base": "https://api.xiaoai.mi.com/v1",
                "env_key": "MIMO_API_KEY",
                "models": ["mimo-v2"],
                "default_model": "mimo-v2",
                "priority": 98,
                "max_tokens": 8192,
                "supports_vision": True,
            },
            "cerebras": {
                "name": "Cerebras",
                "api_base": "https://api.cerebras.ai/v1",
                "env_key": "CEREBRAS_API_KEY",
                "models": ["llama3.1-8b", "llama3.1-70b"],
                "default_model": "llama3.1-8b",
                "priority": 95,
                "max_tokens": 8192,
                "supports_vision": False,
            },
            "deepseek": {
                "name": "DeepSeek",
                "api_base": "https://api.deepseek.com/v1",
                "env_key": "DEEPSEEK_API_KEY",
                "models": ["deepseek-chat", "deepseek-coder"],
                "default_model": "deepseek-chat",
                "priority": 92,
                "max_tokens": 4096,
                "supports_vision": False,
            },
            "gemini": {
                "name": "Google Gemini",
                "api_base": "https://generativelanguage.googleapis.com/v1beta/openai",
                "env_key": "GOOGLE_API_KEY",
                "models": ["gemini-2.0-flash", "gemini-1.5-flash"],
                "default_model": "gemini-2.0-flash",
                "priority": 88,
                "max_tokens": 8192,
                "supports_vision": True,
            },
            "openrouter": {
                "name": "OpenRouter",
                "api_base": "https://openrouter.ai/api/v1",
                "env_key": "OPENROUTER_API_KEY",
                "models": [
                    "meta-llama/llama-3.1-8b-instruct:free",
                    "mistralai/mistral-7b-instruct:free",
                    "google/gemma-2-9b-it:free",
                    "qwen/qwen-2.5-72b-instruct:free",
                ],
                "default_model": "meta-llama/llama-3.1-8b-instruct:free",
                "priority": 85,
                "max_tokens": 4096,
                "supports_vision": False,
            },
            "mistral": {
                "name": "Mistral",
                "api_base": "https://api.mistral.ai/v1",
                "env_key": "MISTRAL_API_KEY",
                "models": ["mistral-small-latest", "open-mistral-7b"],
                "default_model": "mistral-small-latest",
                "priority": 80,
                "max_tokens": 8192,
                "supports_vision": False,
            },
            "siliconflow": {
                "name": "SiliconFlow",
                "api_base": "https://api.siliconflow.cn/v1",
                "env_key": "SILICONFLOW_API_KEY",
                "models": ["Qwen/Qwen2.5-72B-Instruct", "deepseek-ai/DeepSeek-V2.5"],
                "default_model": "Qwen/Qwen2.5-72B-Instruct",
                "priority": 78,
                "max_tokens": 4096,
                "supports_vision": False,
            },
            "nvidia": {
                "name": "NVIDIA NIM",
                "api_base": "https://integrate.api.nvidia.com/v1",
                "env_key": "NVIDIA_API_KEY",
                "models": ["meta/llama-3.1-8b-instruct", "meta/llama-3.1-70b-instruct"],
                "default_model": "meta/llama-3.1-8b-instruct",
                "priority": 75,
                "max_tokens": 4096,
                "supports_vision": False,
            },
            "together": {
                "name": "Together AI",
                "api_base": "https://api.together.xyz/v1",
                "env_key": "TOGETHER_API_KEY",
                "models": ["meta-llama/Llama-3-8b-chat-hf"],
                "default_model": "meta-llama/Llama-3-8b-chat-hf",
                "priority": 70,
                "max_tokens": 4096,
                "supports_vision": False,
            },
            "ollama": {
                "name": "Ollama (Local)",
                "api_base": "http://localhost:11434/v1",
                "env_key": "",
                "models": ["llama3.1", "mistral", "qwen2.5"],
                "default_model": "llama3.1",
                "priority": 60,
                "max_tokens": 4096,
                "supports_vision": False,
                "requires_key": False,
            },
        }
        self._save_providers()

    def _save_providers(self):
        PROVIDERS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(PROVIDERS_FILE, "w", encoding="utf-8") as f:
            json.dump({"providers": self.providers}, f, indent=2, ensure_ascii=False)

    def _create_default_keys(self):
        self.api_keys = {}
        for prov in self.providers.values():
            env_key = prov.get("env_key", "")
            if env_key:
                self.api_keys[env_key] = ""
        self._save_keys()

    def _save_keys(self):
        API_KEYS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(API_KEYS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.api_keys, f, indent=2)

    def _is_provider_configured(self, prov_id: str) -> bool:
        """Check if a provider has its API key configured."""
        prov = self.providers.get(prov_id, {})
        env_key = prov.get("env_key", "")
        requires_key = prov.get("requires_key", True)
        if not requires_key:
            return True
        if not env_key:
            return True
        return bool(self.api_keys.get(env_key, "").strip())

    def get_provider_details(self) -> List[Dict]:
        """Get detailed info for ALL providers (configured or not)."""
        result = []
        for prov_id, prov in self.providers.items():
            env_key = prov.get("env_key", "")
            requires_key = prov.get("requires_key", True)
            configured = self._is_provider_configured(prov_id)
            health = self.health.get(prov_id, ProviderHealth(name=prov_id))
            desc = PROVIDER_DESCRIPTIONS.get(prov_id, {})
            is_free = prov_id in FREE_PROVIDERS

            result.append({
                "id": prov_id,
                "name": prov["name"],
                "models": prov["models"],
                "configured": configured,
                "env_key": env_key,
                "requires_key": requires_key,
                "healthy": health.is_healthy,
                "tested": health.tested,
                "total_requests": health.total_requests,
                "success_rate": round(health.success_rate * 100, 1),
                "avg_latency_ms": round(health.avg_latency * 1000, 1),
                "priority": prov.get("priority", 50),
                "last_error": health.last_error,
                "signup_link": PROVIDER_SIGNUP_LINKS.get(prov_id, ""),
                "description": desc.get("th", ""),
                "free_tier": desc.get("free_tier", ""),
                "is_free": is_free,
                "has_key_in_env": bool(env_key and os.environ.get(env_key, "")),
                "api_base": prov["api_base"],
                "default_model": prov.get("default_model", ""),
                "supports_vision": prov.get("supports_vision", False),
            })
        # Sort: configured first, then by priority
        result.sort(key=lambda x: (not x["configured"], -x["priority"]))
        return result

    def get_available_providers(self) -> List[Dict]:
        """Get only configured and healthy providers."""
        return [p for p in self.get_provider_details() if p["configured"]]

    def pick_provider(self, model: Optional[str] = None, needs_vision: bool = False) -> Optional[tuple]:
        """Pick the best available provider. Returns (provider_id, provider_config, api_key)."""
        available = self.get_available_providers()
        if not available:
            return None

        if model and "/" in model:
            prefix = model.split("/")[0]
            for prov in available:
                if prov["id"] == prefix:
                    prov_config = self.providers[prov["id"]]
                    api_key = self.api_keys.get(prov_config.get("env_key", ""), "")
                    return prov["id"], prov_config, api_key

        if model:
            for prov in available:
                if model in prov["models"]:
                    prov_config = self.providers[prov["id"]]
                    api_key = self.api_keys.get(prov_config.get("env_key", ""), "")
                    return prov["id"], prov_config, api_key

        if needs_vision:
            for prov in available:
                if prov["healthy"] and self.providers[prov["id"]].get("supports_vision"):
                    prov_config = self.providers[prov["id"]]
                    api_key = self.api_keys.get(prov_config.get("env_key", ""), "")
                    return prov["id"], prov_config, api_key

        for prov in available:
            if prov["healthy"]:
                prov_config = self.providers[prov["id"]]
                api_key = self.api_keys.get(prov_config.get("env_key", ""), "")
                return prov["id"], prov_config, api_key

        if available:
            prov = available[0]
            prov_config = self.providers[prov["id"]]
            api_key = self.api_keys.get(prov_config.get("env_key", ""), "")
            return prov["id"], prov_config, api_key

        return None

    def get_cache_key(self, messages: list, model: str) -> str:
        content = json.dumps({"messages": messages, "model": model}, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()

    def get_cached(self, cache_key: str) -> Optional[dict]:
        if cache_key in self.response_cache:
            entry = self.response_cache[cache_key]
            if time.time() - entry["timestamp"] < self.cache_ttl:
                return entry["response"]
            else:
                del self.response_cache[cache_key]
        return None

    def set_cache(self, cache_key: str, response: dict):
        self.response_cache[cache_key] = {
            "response": response,
            "timestamp": time.time(),
        }

    def get_status(self) -> dict:
        uptime = time.time() - self.start_time
        configured_count = sum(1 for p in self.providers if self._is_provider_configured(p))
        healthy_count = sum(1 for p in self.providers if self._is_provider_configured(p) and self.health.get(p, ProviderHealth(name=p)).is_healthy)
        return {
            "uptime_seconds": round(uptime),
            "total_requests": self.total_requests,
            "total_tokens": self.total_tokens,
            "configured_count": configured_count,
            "healthy_count": healthy_count,
            "total_providers": len(self.providers),
            "cache_entries": len(self.response_cache),
            "budget": {
                "enabled": self.budget_enabled,
                "daily_limit": self.daily_limit,
                "daily_spent": self.daily_spent,
                "monthly_limit": self.monthly_limit,
                "monthly_spent": self.monthly_spent,
            },
        }


# ─── Test Provider Connection ──────────────────────────────────

async def test_provider_connection(prov_id: str, prov_config: dict, api_key: str) -> dict:
    """Test if a provider's API key works by sending a minimal request."""
    api_base = prov_config["api_base"]
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    elif prov_config.get("requires_key", True) and prov_id != "ollama":
        return {"success": False, "error": "ไม่ได้ใส่ API Key", "latency_ms": 0}

    default_model = prov_config.get("default_model", prov_config["models"][0])
    payload = {
        "model": default_model,
        "messages": [{"role": "user", "content": "Hi"}],
        "max_tokens": 5,
    }

    try:
        start = time.time()
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{api_base}/chat/completions",
                json=payload,
                headers=headers,
            )
            latency = time.time() - start

            if resp.status_code == 200:
                return {"success": True, "error": None, "latency_ms": round(latency * 1000), "model": default_model}
            elif resp.status_code == 401:
                return {"success": False, "error": "API Key ไม่ถูกต้อง หรือ หมดอายุ", "latency_ms": round(latency * 1000)}
            elif resp.status_code == 403:
                return {"success": False, "error": "API Key ไม่มีสิทธิ์ใช้งาน (403 Forbidden)", "latency_ms": round(latency * 1000)}
            elif resp.status_code == 429:
                return {"success": False, "error": "Rate Limit - ลองใหม่ภายหลัง", "latency_ms": round(latency * 1000)}
            else:
                return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text[:100]}", "latency_ms": round(latency * 1000)}
    except httpx.TimeoutException:
        return {"success": False, "error": "หมดเวลาเชื่อมต่อ (Timeout 30s)", "latency_ms": 30000}
    except Exception as e:
        return {"success": False, "error": str(e)[:200], "latency_ms": 0}


# ─── OpenClaw Integration ──────────────────────────────────────

OPENCLAW_CONFIG_PATH = Path.home() / ".openclaw" / "openclaw.json"

def get_openclaw_config() -> dict:
    """Read current OpenClaw config."""
    if OPENCLAW_CONFIG_PATH.exists():
        try:
            with open(OPENCLAW_CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def apply_openclaw_config(proxy_host: str = "127.0.0.1", proxy_port: int = 8900) -> dict:
    """Auto-apply RouterAI config to OpenClaw."""
    config = get_openclaw_config()
    old_config = json.loads(json.dumps(config))  # Deep copy

    # Set LLM config to point to RouterAI proxy
    if "llm" not in config:
        config["llm"] = {}
    config["llm"]["provider"] = "openai"
    config["llm"]["baseUrl"] = f"http://{proxy_host}:{proxy_port}/v1"
    config["llm"]["apiKey"] = "routerai"

    # Pick best model from available providers
    router = RouterAI()
    available = router.get_available_providers()
    if available:
        best = available[0]
        config["llm"]["model"] = f"{best['id']}/{best['default_model']}"
    else:
        config["llm"]["model"] = "groq/llama-3.3-70b-versatile"

    # Backup old config
    backup_path = OPENCLAW_CONFIG_PATH.with_suffix(".json.bak")
    if OPENCLAW_CONFIG_PATH.exists():
        import shutil
        shutil.copy2(OPENCLAW_CONFIG_PATH, backup_path)

    # Write new config
    OPENCLAW_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OPENCLAW_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    return {"success": True, "old_config": old_config, "new_config": config, "backup_path": str(backup_path)}


# ─── FastAPI App ────────────────────────────────────────────────

router_ai = RouterAI()
app = FastAPI(title="RouterAI", version="1.1.0", description="Smart API Router for OpenClaw")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

WEB_DIR = BASE_DIR / "web"


@app.get("/")
async def root():
    """Serve dashboard or API info."""
    index_path = WEB_DIR / "index.html"
    if index_path.exists():
        return JSONResponse(content={
            "status": "running",
            "message": "RouterAI - OpenAI-compatible API Proxy",
            "dashboard": f"http://127.0.0.1:8899",
            "proxy": f"http://127.0.0.1:8900/v1",
        })
    return JSONResponse(content={"status": "running"})


# ─── OpenAI-compatible endpoints ────────────────────────────────

@app.get("/v1/models")
async def list_models():
    models = []
    for prov_id, prov in router_ai.providers.items():
        for model in prov.get("models", []):
            models.append({
                "id": f"{prov_id}/{model}" if "/" not in model else model,
                "object": "model",
                "created": int(time.time()),
                "owned_by": prov["name"],
            })
    return {"object": "list", "data": models}


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    messages = body.get("messages", [])
    model = body.get("model", "")
    stream = body.get("stream", False)
    max_tokens = body.get("max_tokens", 4096)
    temperature = body.get("temperature", 0.7)

    if not stream:
        cache_key = router_ai.get_cache_key(messages, model)
        cached = router_ai.get_cached(cache_key)
        if cached:
            return JSONResponse(content=cached)

    needs_vision = any(
        isinstance(msg.get("content"), list) and
        any(part.get("type") == "image_url" for part in msg["content"])
        for msg in messages
        if isinstance(msg.get("content"), list)
    )

    errors = []
    tried = set()

    for attempt in range(3):
        picked = router_ai.pick_provider(model=model if attempt == 0 else None, needs_vision=needs_vision)
        if not picked:
            break

        prov_id, prov_config, api_key = picked
        if prov_id in tried:
            continue
        tried.add(prov_id)

        api_base = prov_config["api_base"]
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        elif prov_config.get("requires_key", True) and prov_id != "ollama":
            errors.append(f"{prov_id}: ไม่ได้ใส่ API Key")
            continue

        if model and "/" in model and model.split("/")[0] == prov_id:
            actual_model = model.split("/", 1)[1]
        elif model and model in prov_config.get("models", []):
            actual_model = model
        else:
            actual_model = prov_config.get("default_model", prov_config["models"][0])

        payload = {
            "model": actual_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": stream,
        }

        try:
            start = time.time()
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    f"{api_base}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                latency = time.time() - start

                if resp.status_code == 200:
                    router_ai.health[prov_id].record_success(latency)
                    router_ai.total_requests += 1

                    if stream:
                        async def stream_generator():
                            async for chunk in resp.aiter_bytes():
                                yield chunk
                        return StreamingResponse(stream_generator(), media_type="text/event-stream")
                    else:
                        result = resp.json()
                        usage = result.get("usage", {})
                        router_ai.total_tokens += usage.get("total_tokens", 0)
                        router_ai.set_cache(cache_key, result)
                        return JSONResponse(content=result)
                else:
                    error_msg = f"HTTP {resp.status_code}"
                    if resp.status_code == 401:
                        error_msg = "API Key ไม่ถูกต้อง"
                    elif resp.status_code == 403:
                        error_msg = "ไม่มีสิทธิ์ (403)"
                    elif resp.status_code == 429:
                        error_msg = "Rate Limit"
                    router_ai.health[prov_id].record_failure(error_msg)
                    errors.append(f"{prov_id}: {error_msg}")
                    continue
        except Exception as e:
            router_ai.health[prov_id].record_failure(str(e)[:100])
            errors.append(f"{prov_id}: {str(e)[:100]}")
            continue

    raise HTTPException(status_code=503, detail={"error": "ทุก Provider ใช้ไม่ได้", "errors": errors})


# ─── Dashboard API Endpoints ───────────────────────────────────

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
    """Test a specific provider's API key."""
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
    """Test all configured providers."""
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
    return {
        "status": "healthy" if healthy_count > 0 else "critical",
        "healthy_providers": healthy_count,
        "total_providers": len(results),
        "details": results,
    }


@app.post("/api/openclaw/apply")
async def api_apply_openclaw():
    """Auto-apply RouterAI config to OpenClaw."""
    try:
        result = apply_openclaw_config()
        return result
    except Exception as e:
        raise HTTPException(500, detail=f"ไม่สามารถตั้งค่า OpenClaw ได้: {str(e)}")


@app.get("/api/openclaw/config")
async def api_get_openclaw_config():
    """Get current OpenClaw config."""
    config = get_openclaw_config()
    return {
        "config_exists": OPENCLAW_CONFIG_PATH.exists(),
        "config_path": str(OPENCLAW_CONFIG_PATH),
        "config": config,
    }


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


# ─── Entry Point ────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="RouterAI Proxy Server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8900)
    args = parser.parse_args()

    logger.info(f"🚀 Starting RouterAI on {args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
