#!/usr/bin/env python3
"""
Provider Management - จัดการ API Providers หลายเจ้า
Smart routing, health check, auto-failover
"""

import os
import json
import time
import logging
import hashlib
from pathlib import Path
from threading import Lock
from cachetools import TTLCache

logger = logging.getLogger("openclaw-thai.providers")

PROJECT_ROOT = Path(__file__).parent.parent

class ProviderManager:
    def __init__(self):
        self.providers = {}
        self.health_status = {}
        self.request_counts = {}
        self.error_counts = {}
        self.latency_scores = {}
        self.cache = TTLCache(maxsize=1000, ttl=300)
        self.lock = Lock()
        self.budget_used = 0.0
        self.budget_daily_limit = float(os.getenv("BUDGET_DAILY_LIMIT_USD", "5.00"))
        self.budget_enabled = os.getenv("BUDGET_ENABLED", "false").lower() == "true"
        self.load_providers()

    def load_providers(self):
        """Load provider configuration"""
        config_path = PROJECT_ROOT / "config" / "providers.json"
        try:
            with open(config_path) as f:
                config = json.load(f)
            self.providers = config.get("providers", {})
            self.routing_config = config.get("routing", {})
            logger.info(f"โหลด {len(self.providers)} providers สำเร็จ")
        except Exception as e:
            logger.error(f"โหลด providers.json ล้มเหลว: {e}")
            self.providers = {}

        # Load API keys from environment
        for pid, provider in self.providers.items():
            env_key = provider.get("apiKeyEnv")
            if env_key:
                api_key = os.getenv(env_key, "")
                provider["_apiKey"] = api_key
                if api_key:
                    logger.info(f"  ✅ {provider['name']}: มี API Key")
                else:
                    logger.info(f"  ⬜ {provider['name']}: ยังไม่มี API Key")
            else:
                provider["_apiKey"] = ""
                logger.info(f"  🏠 {provider['name']}: ไม่ต้องใช้ Key")

    def get_available_providers(self):
        """Get list of providers with valid API keys, sorted by priority"""
        available = []
        for pid, provider in self.providers.items():
            if not provider.get("enabled", True):
                continue
            env_key = provider.get("apiKeyEnv")
            if env_key and not provider.get("_apiKey"):
                continue
            available.append((pid, provider))

        # Sort by priority (higher = better)
        available.sort(key=lambda x: x[1].get("priority", 0), reverse=True)
        return available

    def get_free_models(self):
        """Get all free models across all providers"""
        free = []
        for pid, provider in self.get_available_providers():
            for model in provider.get("freeModels", []):
                free.append({
                    "provider": pid,
                    "providerName": provider["name"],
                    "emoji": provider["emoji"],
                    "model": model,
                    "fullModel": f"{pid}/{model}",
                    "cost": "free"
                })
        return free

    def get_all_models(self):
        """Get all models across all providers"""
        models = []
        for pid, provider in self.get_available_providers():
            for model in provider.get("models", []):
                is_free = model in provider.get("freeModels", [])
                models.append({
                    "provider": pid,
                    "providerName": provider["name"],
                    "emoji": provider["emoji"],
                    "model": model,
                    "fullModel": f"{pid}/{model}",
                    "cost": "free" if is_free else provider.get("cost", "paid"),
                    "healthy": self.health_status.get(pid, {}).get("healthy", None)
                })
        return models

    def select_provider(self, model_name=None, prefer_free=True):
        """
        Smart provider selection
        - If model_name specified, find provider that has it
        - Otherwise, select best available provider
        """
        available = self.get_available_providers()
        if not available:
            return None, None

        if model_name:
            # Find providers that support this model
            candidates = []
            for pid, provider in available:
                if model_name in provider.get("models", []):
                    score = self._calculate_score(pid, provider, prefer_free, model_name)
                    candidates.append((score, pid, provider, model_name))
            if candidates:
                candidates.sort(reverse=True, key=lambda x: x[0])
                _, pid, provider, model = candidates[0]
                return pid, provider, model

        # No specific model - select best provider + its top free model
        if prefer_free:
            for pid, provider in available:
                free = provider.get("freeModels", [])
                if free:
                    return pid, provider, free[0]

        # Fallback to first available
        pid, provider = available[0]
        models = provider.get("models", [])
        return pid, provider, models[0] if models else None

    def _calculate_score(self, pid, provider, prefer_free, model_name):
        """Calculate routing score for a provider"""
        score = provider.get("priority", 50)

        # Prefer free models
        if prefer_free and model_name in provider.get("freeModels", []):
            score += 20

        # Penalize unhealthy providers
        health = self.health_status.get(pid, {})
        if not health.get("healthy", True):
            score -= 50

        # Penalize high error rates
        errors = self.error_counts.get(pid, 0)
        score -= min(errors * 5, 30)

        # Factor in latency
        latency = self.latency_scores.get(pid, 1000)
        score -= min(latency / 100, 20)

        return score

    def record_success(self, pid, latency_ms):
        """Record successful request"""
        with self.lock:
            self.request_counts[pid] = self.request_counts.get(pid, 0) + 1
            # Exponential moving average for latency
            old = self.latency_scores.get(pid, latency_ms)
            self.latency_scores[pid] = old * 0.7 + latency_ms * 0.3
            # Reset errors on success
            self.error_counts[pid] = max(0, self.error_counts.get(pid, 0) - 1)

    def record_error(self, pid):
        """Record failed request"""
        with self.lock:
            self.error_counts[pid] = self.error_counts.get(pid, 0) + 1
            errors = self.error_counts[pid]
            logger.warning(f"Provider {pid} error #{errors}")

            # Auto-disable after too many consecutive errors
            if errors >= 5:
                logger.error(f"Provider {pid} ถูกปิดชั่วคราว (errors >= 5)")
                self.health_status[pid] = {"healthy": False, "reason": "too many errors"}

    def get_cache_key(self, messages, model):
        """Generate cache key from request"""
        content = json.dumps({"messages": messages, "model": model}, sort_keys=True)
        return hashlib.md5(content.encode()).hexdigest()

    def get_cached(self, cache_key):
        """Get cached response"""
        return self.cache.get(cache_key)

    def set_cache(self, cache_key, response):
        """Cache response"""
        self.cache[cache_key] = response

    def get_stats(self):
        """Get provider statistics"""
        stats = {}
        for pid, provider in self.providers.items():
            stats[pid] = {
                "name": provider["name"],
                "emoji": provider["emoji"],
                "enabled": provider.get("enabled", True),
                "hasKey": bool(provider.get("_apiKey")),
                "priority": provider.get("priority", 0),
                "cost": provider.get("cost", "unknown"),
                "requests": self.request_counts.get(pid, 0),
                "errors": self.error_counts.get(pid, 0),
                "avgLatency": round(self.latency_scores.get(pid, 0)),
                "healthy": self.health_status.get(pid, {}).get("healthy", None),
                "models": provider.get("models", []),
                "freeModels": provider.get("freeModels", [])
            }
        return stats

    def update_provider_key(self, pid, api_key):
        """Update API key for a provider"""
        if pid in self.providers:
            self.providers[pid]["_apiKey"] = api_key
            # Save to .env file
            env_key = self.providers[pid].get("apiKeyEnv")
            if env_key:
                self._save_env_key(env_key, api_key)
            return True
        return False

    def _save_env_key(self, env_key, value):
        """Save API key to .env file"""
        env_path = PROJECT_ROOT / "config" / ".env"
        lines = []
        found = False

        if env_path.exists():
            with open(env_path) as f:
                lines = f.readlines()

        new_lines = []
        for line in lines:
            if line.strip().startswith(f"{env_key}="):
                new_lines.append(f"{env_key}={value}\n")
                found = True
            else:
                new_lines.append(line)

        if not found:
            new_lines.append(f"{env_key}={value}\n")

        with open(env_path, "w") as f:
            f.writelines(new_lines)

    def test_provider(self, pid):
        """Test if a provider is working"""
        provider = self.providers.get(pid)
        if not provider:
            return {"success": False, "error": "ไม่พบ Provider"}

        api_key = provider.get("_apiKey")
        env_key = provider.get("apiKeyEnv")
        if env_key and not api_key:
            return {"success": False, "error": "ยังไม่ได้ใส่ API Key"}

        base_url = provider.get("baseUrl", "")
        test_model = provider.get("models", ["test"])[0]

        try:
            import requests as req
            start = time.time()
            headers = {"Content-Type": "application/json"}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            resp = req.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json={
                    "model": test_model,
                    "messages": [{"role": "user", "content": "Say hi"}],
                    "max_tokens": 10
                },
                timeout=15
            )
            latency = round((time.time() - start) * 1000)

            if resp.status_code == 200:
                self.health_status[pid] = {"healthy": True, "latency": latency}
                self.latency_scores[pid] = latency
                return {"success": True, "latency": latency, "model": test_model}
            else:
                self.health_status[pid] = {"healthy": False, "reason": resp.text[:200]}
                return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text[:200]}"}

        except Exception as e:
            self.health_status[pid] = {"healthy": False, "reason": str(e)}
            return {"success": False, "error": str(e)}
