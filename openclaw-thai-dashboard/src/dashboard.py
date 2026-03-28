#!/usr/bin/env python3
"""
Dashboard Server - Web UI ภาษาไทยสำหรับจัดการ OpenClaw + API Router
"""

import os
import json
import time
import logging
from pathlib import Path

from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS

from providers import ProviderManager
from config_manager import ConfigManager

logger = logging.getLogger("openclaw-thai.dashboard")

PROJECT_ROOT = Path(__file__).parent.parent
WEB_DIR = PROJECT_ROOT / "web"

# Shared instances
pm = ProviderManager()
cm = ConfigManager()


def create_dashboard_app():
    app = Flask(__name__, static_folder=str(WEB_DIR), static_url_path="")
    CORS(app)

    @app.route("/")
    def index():
        return send_from_directory(str(WEB_DIR), "index.html")

    @app.route("/api/dashboard/overview")
    def overview():
        """หน้ารวมภาพ - Overview"""
        available = pm.get_available_providers()
        all_models = pm.get_all_models()
        free_models = pm.get_free_models()
        model_config = cm.get_model_config()
        channels = cm.get_channels()

        return jsonify({
            "providers": {
                "total": len(pm.providers),
                "available": len(available),
                "withKeys": sum(1 for _, p in available if p.get("_apiKey")),
            },
            "models": {
                "total": len(all_models),
                "free": len(free_models),
            },
            "currentModel": model_config["model"],
            "channels": channels,
            "budget": {
                "enabled": pm.budget_enabled,
                "used": pm.budget_used,
                "limit": pm.budget_daily_limit,
            },
            "system": cm.get_system_info(),
        })

    @app.route("/api/dashboard/providers")
    def providers():
        """หน้าจัดการ Providers"""
        return jsonify(pm.get_stats())

    @app.route("/api/dashboard/models")
    def models():
        """หน้ารายการโมเดล"""
        return jsonify({
            "all": pm.get_all_models(),
            "free": pm.get_free_models(),
            "current": cm.get_model_config(),
        })

    @app.route("/api/dashboard/channels")
    def channels():
        """หน้าจัดการ Channels"""
        return jsonify(cm.get_channels())

    @app.route("/api/dashboard/skills")
    def skills():
        """หน้ารายการ Skills"""
        return jsonify(cm.get_skills())

    @app.route("/api/dashboard/config")
    def config():
        """หน้าตั้งค่า"""
        return jsonify({
            "model": cm.get_model_config(),
            "channels": cm.get_channels(),
            "system": cm.get_system_info(),
            "configPath": str(cm.config_path),
        })

    @app.route("/api/provider/<pid>/test", methods=["POST"])
    def test_provider(pid):
        """ทดสอบ Provider"""
        return jsonify(pm.test_provider(pid))

    @app.route("/api/provider/<pid>/key", methods=["POST"])
    def set_provider_key(pid):
        """ตั้งค่า API Key"""
        body = request.get_json(force=True)
        api_key = body.get("apiKey", "")
        if pm.update_provider_key(pid, api_key):
            return jsonify({"success": True, "message": f"บันทึก Key สำหรับ {pid} แล้ว"})
        return jsonify({"success": False, "error": "ไม่พบ Provider"}), 404

    @app.route("/api/provider/<pid>/toggle", methods=["POST"])
    def toggle_provider(pid):
        """เปิด/ปิด Provider"""
        if pid in pm.providers:
            pm.providers[pid]["enabled"] = not pm.providers[pid].get("enabled", True)
            state = "เปิด" if pm.providers[pid]["enabled"] else "ปิด"
            return jsonify({"success": True, "enabled": pm.providers[pid]["enabled"], "message": f"{state} {pid} แล้ว"})
        return jsonify({"success": False, "error": "ไม่พบ Provider"}), 404

    @app.route("/api/config/apply-proxy", methods=["POST"])
    def apply_proxy():
        """ตั้งค่า OpenClaw ให้ใช้ Proxy"""
        proxy_port = int(os.getenv("PROXY_PORT", "8876"))
        result = cm.apply_proxy_config(proxy_port)
        return jsonify(result)

    @app.route("/api/config/reload", methods=["POST"])
    def reload_config():
        """โหลด config ใหม่"""
        pm.load_providers()
        cm.load()
        return jsonify({"success": True, "message": "โหลด config ใหม่แล้ว"})

    @app.route("/api/stats/routing")
    def routing_stats():
        """สถิติการ Route"""
        return jsonify({
            "requests": dict(pm.request_counts),
            "errors": dict(pm.error_counts),
            "latencies": {k: round(v) for k, v in pm.latency_scores.items()},
            "cache": len(pm.cache),
        })

    return app
