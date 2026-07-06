"""
app.py – Flask web server for the Startup Blueprint Generator.

Routes
------
GET  /                    → Serve the single-page frontend
POST /api/generate        → Accept a startup idea, run all 6 agents, return JSON
GET  /api/health          → Simple liveness check

Demo Mode
---------
Set  DEMO_MODE=true  in your .env to always use the built-in demo engine.
If the real API credentials are missing or the API returns an error, the
server automatically falls back to demo mode so the UI always works.
"""

from __future__ import annotations

import logging
import os

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from startup_blueprint.demo_engine import generate_blueprint as demo_generate

# ─────────────────────────────────────────────────────────────────────────────
# App setup
# ─────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder="static", static_url_path="/static")
CORS(app)

# ─────────────────────────────────────────────────────────────────────────────
# Determine mode: real API or demo
# ─────────────────────────────────────────────────────────────────────────────

_DEMO_MODE: bool = os.getenv("DEMO_MODE", "false").lower() == "true"
_orchestrator = None

if not _DEMO_MODE:
    # Try to load real credentials; silently fall back to demo if they're absent
    try:
        from startup_blueprint.config import load_config
        from startup_blueprint.blueprint_agents import BlueprintOrchestrator
        from startup_blueprint.orchestrate_client import APIError
        _config = load_config()
        _orchestrator = BlueprintOrchestrator(_config)
        logger.info("Live IBM watsonx Orchestrate credentials loaded — running in LIVE mode.")
    except EnvironmentError as _err:
        logger.warning("Credentials incomplete (%s) — falling back to DEMO mode.", _err)
        _DEMO_MODE = True
    except Exception as _err:  # noqa: BLE001
        logger.warning("Config load failed (%s) — falling back to DEMO mode.", _err)
        _DEMO_MODE = True

if _DEMO_MODE:
    logger.info("Running in DEMO mode — blueprint content is generated locally.")

# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    """Serve the main frontend page."""
    return send_from_directory("static", "index.html")


@app.route("/api/health")
def health():
    """Liveness check — also reports which mode is active."""
    return jsonify({
        "status":    "ok",
        "mode":      "demo" if _DEMO_MODE else "live",
        "live_ready": _orchestrator is not None,
    }), 200


@app.route("/api/generate", methods=["POST"])
def generate():
    """
    Receive a startup idea and return a full 6-agent blueprint.

    Request body (JSON)
    -------------------
    {
        "idea":     "Your startup idea text",         # required
        "industry": "FinTech",                        # optional
        "stage":    "idea | mvp | growth | scale"    # optional
    }

    Response (JSON)
    ---------------
    {
        "startup_idea": str,
        "demo_mode":    bool,
        "sections": {
            "startup_plan":        str,
            "market_intelligence": str,
            "business_strategy":   str,
            "finance_funding":     str,
            "go_to_market":        str,
            "pitch_deck":          str
        }
    }
    """
    data  = request.get_json(silent=True) or {}
    idea  = (data.get("idea") or "").strip()
    if not idea:
        return jsonify({"error": "The 'idea' field is required."}), 400

    industry = data.get("industry") or None
    stage    = data.get("stage")    or None

    # ── Demo mode path ────────────────────────────────────────────────────────
    if _DEMO_MODE:
        logger.info("DEMO generate: %.80s ...", idea)
        blueprint = demo_generate(idea, industry_hint=industry, stage_hint=stage)
        return jsonify(blueprint), 200

    # ── Live API path ─────────────────────────────────────────────────────────
    context: dict = {}
    if industry:
        context["industry"] = industry
    if stage:
        context["stage"] = stage

    logger.info("LIVE generate: %.80s ...", idea)
    try:
        blueprint = _orchestrator.generate(
            startup_idea=idea,
            additional_context=context or None,
        )
        blueprint["demo_mode"] = False
        return jsonify(blueprint), 200

    except EnvironmentError as exc:
        logger.error("Auth error: %s", exc)
        # Auto-fallback to demo on auth errors (e.g. WXO-PROXY-11112E)
        logger.info("Falling back to DEMO mode due to auth error.")
        blueprint = demo_generate(idea, industry_hint=industry, stage_hint=stage)
        blueprint["api_error"] = str(exc)
        return jsonify(blueprint), 200

    except Exception as exc:  # noqa: BLE001
        logger.error("Live API error: %s — falling back to demo.", exc)
        blueprint = demo_generate(idea, industry_hint=industry, stage_hint=stage)
        blueprint["api_error"] = str(exc)
        return jsonify(blueprint), 200


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port  = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    mode  = "DEMO" if _DEMO_MODE else "LIVE"
    logger.info("Startup Blueprint Generator [%s] on http://localhost:%d", mode, port)
    app.run(host="0.0.0.0", port=port, debug=debug)
