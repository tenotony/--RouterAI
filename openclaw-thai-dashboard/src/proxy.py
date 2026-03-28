#!/usr/bin/env python3
"""
API Proxy Server - OpenAI-compatible proxy with smart routing
Handles request forwarding, caching, failover, and cost tracking
"""

import os
import json
import time
import logging
import uuid
from pathlib import Path

from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
import requests as http_requests

from providers import ProviderManager

logger = logging.getLogger("openclaw-thai.proxy")

PROJECT_ROOT = Path(__file__).parent.parent

# Global provider manager instance
pm = ProviderManager()


def create_proxy_app():
    app = Flask(__name__)
    CORS(app, resources={r"/*": {"origins": "*"}})

    @app.route("/v1/chat/completions", methods=["POST"])
    def chat_completions():
        """OpenAI-compatible chat completions endpoint"""
        try:
            body = request.get_json(force=True)
        except Exception:
            return jsonify({"error": {"message": "Invalid JSON body"}}), 400

        messages = body.get("messages", [])
        requested_model = body.get("model", "")
        stream = body.get("stream", False)

        # Parse model: "provider/model" or just "model"
        provider_id = None
        model_name = requested_model

        if "/" in requested_model:
            parts = requested_model.split("/", 1)
            provider_id = parts[0]
            model_name = parts[1]

        # Check cache first
        if pm.routing_config.get("cacheEnabled", True):
            cache_key = pm.get_cache_key(messages, requested_model)
            cached = pm.get_cached(cache_key)
            if cached:
                logger.info(f"📦 Cache HIT for {requested_model}")
                if stream:
                    return _stream_cached(cached)
                return jsonify(cached)

        # Select provider
        if provider_id and provider_id in pm.providers:
            provider = pm.providers[provider_id]
            if model_name not in provider.get("models", []):
                return jsonify({
                    "error": {"message": f"Model '{model_name}' not found in provider '{provider_id}'"}
                }), 404
        else:
            # Smart routing
            prefer_free = pm.routing_config.get("preferFree", True)
            result = pm.select_provider(model_name if not provider_id else None, prefer_free)
            if not result or not result[0]:
                return jsonify({"error": {"message": "ไม่มี Provider ที่ใช้งานได้ กรุณาใส่ API Key อย่างน้อย 1 ตัว"}}), 503
            provider_id, provider, model_name = result

        # Forward request
        return _forward_request(provider_id, provider, model_name, body, messages, stream)

    @app.route("/v1/models", methods=["GET"])
    def list_models():
        """List all available models"""
        models = pm.get_all_models()
        return jsonify({
            "object": "list",
            "data": [
                {
                    "id": m["fullModel"],
                    "object": "model",
                    "created": 0,
                    "owned_by": m["provider"],
                    "cost": m["cost"]
                }
                for m in models
            ]
        })

    @app.route("/health", methods=["GET"])
    def health():
        """Health check endpoint"""
        available = pm.get_available_providers()
        return jsonify({
            "status": "ok",
            "providers": len(available),
            "totalProviders": len(pm.providers),
            "budgetEnabled": pm.budget_enabled,
            "budgetUsed": pm.budget_used
        })

    @app.route("/api/providers", methods=["GET"])
    def api_providers():
        """Get provider stats (used by dashboard)"""
        return jsonify(pm.get_stats())

    @app.route("/api/providers/<pid>/test", methods=["POST"])
    def api_test_provider(pid):
        """Test a provider"""
        result = pm.test_provider(pid)
        return jsonify(result)

    @app.route("/api/providers/<pid>/key", methods=["POST"])
    def api_set_key(pid):
        """Update provider API key"""
        body = request.get_json(force=True)
        api_key = body.get("apiKey", "")
        if pm.update_provider_key(pid, api_key):
            return jsonify({"success": True})
        return jsonify({"success": False, "error": "ไม่พบ Provider"}), 404

    @app.route("/api/models/free", methods=["GET"])
    def api_free_models():
        """Get all free models"""
        return jsonify(pm.get_free_models())

    @app.route("/api/stats", methods=["GET"])
    def api_stats():
        """Get routing statistics"""
        return jsonify({
            "requests": dict(pm.request_counts),
            "errors": dict(pm.error_counts),
            "latencies": {k: round(v) for k, v in pm.latency_scores.items()},
            "cacheSize": len(pm.cache),
            "budgetUsed": pm.budget_used
        })

    return app


def _forward_request(provider_id, provider, model_name, body, messages, stream):
    """Forward request to the selected provider with retry + failover"""
    base_url = provider.get("baseUrl", "")
    api_key = provider.get("_apiKey", "")

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    # Prepare request body
    forward_body = dict(body)
    forward_body["model"] = model_name

    max_retries = pm.routing_config.get("maxRetries", 3)
    timeout = pm.routing_config.get("timeoutSeconds", 60)

    for attempt in range(max_retries):
        try:
            start = time.time()

            if stream:
                return _stream_response(base_url, headers, forward_body, timeout, provider_id, start)

            resp = http_requests.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=forward_body,
                timeout=timeout
            )
            latency = (time.time() - start) * 1000

            if resp.status_code == 200:
                pm.record_success(provider_id, latency)
                result = resp.json()

                # Cache response
                if pm.routing_config.get("cacheEnabled", True):
                    cache_key = pm.get_cache_key(messages, body.get("model", ""))
                    pm.set_cache(cache_key, result)

                logger.info(f"✅ {provider_id}/{model_name} - {round(latency)}ms")
                return jsonify(result)

            elif resp.status_code == 429:
                # Rate limited - try next provider
                logger.warning(f"⚠️ {provider_id} rate limited, trying next...")
                pm.record_error(provider_id)
                continue

            else:
                pm.record_error(provider_id)
                logger.error(f"❌ {provider_id} HTTP {resp.status_code}: {resp.text[:200]}")

                # Try failover
                if attempt < max_retries - 1:
                    result = pm.select_provider(None, pm.routing_config.get("preferFree", True))
                    if result and result[0] and result[0] != provider_id:
                        provider_id, provider, model_name = result
                        base_url = provider.get("baseUrl", "")
                        api_key = provider.get("_apiKey", "")
                        headers = {"Content-Type": "application/json"}
                        if api_key:
                            headers["Authorization"] = f"Bearer {api_key}"
                        forward_body["model"] = model_name
                        continue

                return jsonify({"error": {"message": f"Provider error: HTTP {resp.status_code}"}}), resp.status_code

        except http_requests.exceptions.Timeout:
            pm.record_error(provider_id)
            logger.warning(f"⏰ {provider_id} timeout")
            if attempt < max_retries - 1:
                continue
            return jsonify({"error": {"message": "Request timeout"}}), 504

        except Exception as e:
            pm.record_error(provider_id)
            logger.error(f"❌ {provider_id} error: {e}")
            if attempt < max_retries - 1:
                continue
            return jsonify({"error": {"message": str(e)}}), 502

    return jsonify({"error": {"message": "All providers failed"}}), 503


def _stream_response(base_url, headers, body, timeout, provider_id, start):
    """Stream response from provider"""
    try:
        resp = http_requests.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json=body,
            timeout=timeout,
            stream=True
        )

        if resp.status_code != 200:
            pm.record_error(provider_id)
            return jsonify({"error": {"message": f"HTTP {resp.status_code}"}}), resp.status_code

        def generate():
            for chunk in resp.iter_lines():
                if chunk:
                    yield chunk.decode() + "\n\n"
            latency = (time.time() - start) * 1000
            pm.record_success(provider_id, latency)

        return Response(
            stream_with_context(generate()),
            content_type="text/event-stream"
        )

    except Exception as e:
        pm.record_error(provider_id)
        return jsonify({"error": {"message": str(e)}}), 502


def _stream_cached(cached):
    """Stream a cached response"""
    def generate():
        choice = cached.get("choices", [{}])[0]
        message = choice.get("message", {})
        content = message.get("content", "")
        chunk = {
            "id": f"cached-{uuid.uuid4().hex[:8]}",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "choices": [{"delta": {"content": content}, "index": 0, "finish_reason": "stop"}]
        }
        yield f"data: {json.dumps(chunk)}\n\n"
        yield "data: [DONE]\n\n"

    return Response(
        stream_with_context(generate()),
        content_type="text/event-stream"
    )
