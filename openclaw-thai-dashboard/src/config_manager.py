#!/usr/bin/env python3
"""
OpenClaw Config Manager - อ่าน/เขียน config ของ OpenClaw
"""

import os
import json
import shutil
import logging
from pathlib import Path

logger = logging.getLogger("openclaw-thai.config")

OPENCLAW_HOME = Path(os.path.expanduser(os.getenv("OPENCLAW_HOME", "~/.openclaw")))
OPENCLAW_CONFIG = OPENCLAW_HOME / "openclaw.json"


class ConfigManager:
    def __init__(self):
        self.config_path = OPENCLAW_CONFIG
        self.config = {}
        self.load()

    def load(self):
        """Load OpenClaw config"""
        if self.config_path.exists():
            try:
                with open(self.config_path) as f:
                    self.config = json.load(f)
                logger.info(f"โหลด config จาก {self.config_path}")
            except Exception as e:
                logger.error(f"โหลด config ล้มเหลว: {e}")
                self.config = {}
        else:
            logger.warning(f"ไม่พบ config ที่ {self.config_path}")

    def save(self):
        """Save OpenClaw config (with backup)"""
        if self.config_path.exists():
            backup = self.config_path.with_suffix(".json.bak")
            shutil.copy2(self.config_path, backup)
            logger.info(f"สำรอง config ไป {backup}")

        with open(self.config_path, "w") as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
        logger.info("บันทึก config สำเร็จ")

    def get_model_config(self):
        """Get current model configuration"""
        agents = self.config.get("agents", {})
        defaults = agents.get("defaults", {})
        return {
            "model": defaults.get("model", "ยังไม่ได้ตั้งค่า"),
            "imageModel": defaults.get("imageModel", "ยังไม่ได้ตั้งค่า"),
            "models": defaults.get("models", {}),
            "timeoutSeconds": defaults.get("timeoutSeconds", 600),
            "contextTokens": defaults.get("contextTokens", 200000),
            "maxConcurrent": defaults.get("maxConcurrent", 1),
        }

    def get_channels(self):
        """Get channel configuration"""
        channels = self.config.get("channels", {})
        result = {}
        for ch_name, ch_config in channels.items():
            if ch_name == "defaults" or ch_name == "modelByChannel":
                continue
            if isinstance(ch_config, dict):
                result[ch_name] = {
                    "enabled": ch_config.get("enabled", True),
                    "hasToken": bool(ch_config.get("botToken") or ch_config.get("token")),
                    "dmPolicy": ch_config.get("dmPolicy", "pairing"),
                    "groupPolicy": ch_config.get("groupPolicy", "allowlist"),
                }
        return result

    def get_skills(self):
        """Get installed skills"""
        skills_dir = OPENCLAW_HOME / "skills"
        skills = []
        if skills_dir.exists():
            for item in skills_dir.iterdir():
                if item.is_dir():
                    skill_md = item / "SKILL.md"
                    skills.append({
                        "name": item.name,
                        "hasSkillMd": skill_md.exists(),
                        "path": str(item)
                    })
        # Also check built-in skills
        builtin = Path("/usr/lib/node_modules/openclaw/skills")
        if builtin.exists():
            for item in builtin.iterdir():
                if item.is_dir():
                    skills.append({
                        "name": item.name,
                        "builtin": True,
                        "path": str(item)
                    })
        return skills

    def apply_proxy_config(self, proxy_port=8876):
        """Configure OpenClaw to use the local proxy"""
        if not self.config:
            return {"success": False, "error": "ไม่พบ OpenClaw config"}

        # Set model to use proxy
        agents = self.config.setdefault("agents", {})
        defaults = agents.setdefault("defaults", {})
        models = defaults.setdefault("models", {})

        # Get free models from proxy
        proxy_url = f"http://127.0.0.1:{proxy_port}"
        try:
            import requests as req
            resp = req.get(f"{proxy_url}/api/models/free", timeout=5)
            free_models = resp.json()
        except Exception as e:
            return {"success": False, "error": f"เชื่อม Proxy ไม่ได้: {e}"}

        if not free_models:
            return {"success": False, "error": "ไม่มีโมเดลฟรีที่ใช้ได้ กรุณาใส่ API Key ก่อน"}

        # Build fallback chain from free models
        primary = free_models[0]["fullModel"]
        fallbacks = [m["fullModel"] for m in free_models[1:6]]

        defaults["model"] = {
            "primary": primary,
            "fallbacks": fallbacks
        }

        # Add model aliases
        for m in free_models[:10]:
            full = m["fullModel"]
            models[full] = {
                "alias": m["model"].split("/")[-1][:20] if "/" in m["model"] else m["model"][:20]
            }

        self.save()
        return {
            "success": True,
            "primary": primary,
            "fallbacks": fallbacks,
            "message": f"ตั้งค่าโมเดลหลัก: {primary}\nFallbacks: {', '.join(fallbacks[:3])}"
        }

    def get_system_info(self):
        """Get system information"""
        import platform
        return {
            "platform": platform.system(),
            "platformVersion": platform.version(),
            "python": platform.python_version(),
            "configPath": str(self.config_path),
            "configExists": self.config_path.exists(),
            "openclawHome": str(OPENCLAW_HOME),
        }
