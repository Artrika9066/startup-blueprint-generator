"""
config.py – Load and validate environment variables for the
Startup Blueprint Generator that talks to IBM watsonx Orchestrate.
"""

import os
import re
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

# Matches the UUID in a watsonx Orchestrate instance URL, e.g.
# https://api.eu-gb.watson-orchestrate.cloud.ibm.com/instances/146ebbaf-8fc9-4997-89c4-5e2200514a28
# or just a bare UUID such as 146ebbaf-8fc9-4997-89c4-5e2200514a28
_UUID_RE = re.compile(
    r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})",
    re.IGNORECASE,
)

# Similarly, agent IDs may be pasted as full UI URLs, e.g.
# https://eu-gb.watson-orchestrate.cloud.ibm.com/build/agent/edit/<uuid>
# We always want just the bare UUID at the end.


def _extract_uuid(value: str) -> str:
    """Return the last UUID found in *value*, or *value* unchanged."""
    matches = _UUID_RE.findall(value.strip())
    return matches[-1] if matches else value.strip()


@dataclass(frozen=True)
class Config:
    # ------------------------------------------------------------------ #
    # IBM watsonx Orchestrate credentials                                  #
    # ------------------------------------------------------------------ #
    wxo_base_url: str       # e.g. https://api.eu-gb.watson-orchestrate.cloud.ibm.com
    wxo_api_key: str        # IBM Cloud API key
    wxo_instance_id: str    # Bare instance UUID → sent as X-IBM-Instance-ID

    # ------------------------------------------------------------------ #
    # Agent UUIDs inside your Orchestrate instance                        #
    # ------------------------------------------------------------------ #
    planner_agent_id: str   # Startup Planner Agent UUID
    market_agent_id: str    # Market Intelligence Agent UUID
    strategy_agent_id: str  # Business Strategy Agent UUID
    finance_agent_id: str   # Finance and Funding Agent UUID
    gtm_agent_id: str       # Go-To-Market Agent UUID
    pitch_agent_id: str     # Pitch Deck Agent UUID

    # ------------------------------------------------------------------ #
    # Runtime knobs                                                        #
    # ------------------------------------------------------------------ #
    timeout_seconds: int = 120


def load_config() -> Config:
    """
    Read all required values from environment variables.

    Agent ID values and the instance ID may be supplied as either bare
    UUIDs or full watsonx Orchestrate UI/API URLs — the UUID is extracted
    automatically either way.
    """
    required = {
        "WXO_BASE_URL":      "wxo_base_url",
        "WXO_API_KEY":       "wxo_api_key",
        "WXO_INSTANCE_ID":   "wxo_instance_id",
        "PLANNER_AGENT_ID":  "planner_agent_id",
        "MARKET_AGENT_ID":   "market_agent_id",
        "STRATEGY_AGENT_ID": "strategy_agent_id",
        "FINANCE_AGENT_ID":  "finance_agent_id",
        "GTM_AGENT_ID":      "gtm_agent_id",
        "PITCH_AGENT_ID":    "pitch_agent_id",
    }

    # UUID-bearing fields — extract just the bare UUID
    uuid_fields = {
        "wxo_instance_id",
        "planner_agent_id", "market_agent_id", "strategy_agent_id",
        "finance_agent_id", "gtm_agent_id",    "pitch_agent_id",
    }

    values: dict = {}
    missing: list[str] = []

    for env_key, field in required.items():
        raw = os.getenv(env_key, "").strip()
        if not raw:
            missing.append(env_key)
            values[field] = raw
            continue
        values[field] = _extract_uuid(raw) if field in uuid_fields else raw

    if missing:
        raise EnvironmentError(
            f"Missing required environment variable(s): {', '.join(missing)}\n"
            "Copy .env.example to .env and fill in the values."
        )

    timeout = int(os.getenv("WXO_TIMEOUT_SECONDS", "120"))
    return Config(**values, timeout_seconds=timeout)
