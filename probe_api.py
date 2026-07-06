"""
probe_api.py – Diagnostic script for IBM watsonx Orchestrate API.

Runs against your live credentials and probes EVERY known candidate
endpoint variant, printing the exact HTTP status + response body for each.

Usage
-----
    python probe_api.py
    python probe_api.py --idea "A SaaS tool for freelancers"

What it tests
-------------
For the first agent (PLANNER_AGENT_ID) it tries all of:
  1. POST /v1/agents/{agent_id}/chat               ← current implementation
  2. POST /v1/agents/{agent_id}/chat  (body: input.text only, no message_type)
  3. POST /v2/agents/{agent_id}/chat
  4. POST /v1/agents/{agent_id}/runs
  5. POST /v1/agent/chat              (agent_id in body)
  6. POST /v1/chat                    (agent_id in body)
  7. GET  /v1/agents/{agent_id}       (check agent exists at all)
  8. GET  /v1/agents                  (list all agents)

It also checks that IAM token exchange works and prints the token prefix
so you can verify auth is succeeding before the Orchestrate calls.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import textwrap

import requests
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────────────
BASE_URL     = os.getenv("WXO_BASE_URL",     "").rstrip("/")
API_KEY      = os.getenv("WXO_API_KEY",      "")
INSTANCE_ID  = os.getenv("WXO_INSTANCE_ID",  "")
PLANNER_ID   = os.getenv("PLANNER_AGENT_ID", "")

# Extract bare UUID from any value (handles full UI URLs)
import re as _re
_UUID_PAT = _re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", _re.I)
def _uuid(v: str) -> str:
    m = _UUID_PAT.findall(v)
    return m[-1] if m else v

INSTANCE_ID = _uuid(INSTANCE_ID)
AGENT_ID    = _uuid(PLANNER_ID)

TIMEOUT = 30


# ─────────────────────────────────────────────────────────────────────────────
# IAM token
# ─────────────────────────────────────────────────────────────────────────────
def get_iam_token(api_key: str) -> str:
    print("\n[1/2] Fetching IAM token …")
    resp = requests.post(
        "https://iam.cloud.ibm.com/identity/token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
            "apikey": api_key,
        },
        timeout=TIMEOUT,
    )
    if resp.status_code != 200:
        print(f"  FAIL  HTTP {resp.status_code}")
        print(f"  Body: {resp.text[:500]}")
        sys.exit(1)
    token = resp.json()["access_token"]
    print(f"  OK    token prefix: {token[:20]}…")
    return token


# ─────────────────────────────────────────────────────────────────────────────
# Probe helpers
# ─────────────────────────────────────────────────────────────────────────────
def _fmt(resp: requests.Response) -> str:
    try:
        body = json.dumps(resp.json(), indent=2)
    except Exception:
        body = resp.text
    return body[:2000]   # cap at 2 kB per result


def probe(label: str, method: str, url: str, token: str,
          body: dict | None = None, extra_headers: dict | None = None) -> None:
    headers = {
        "Authorization":     f"Bearer {token}",
        "Content-Type":      "application/json",
        "Accept":            "application/json",
        "X-IBM-Instance-ID": INSTANCE_ID,
    }
    if extra_headers:
        headers.update(extra_headers)

    sep = "─" * 72
    print(f"\n{sep}")
    print(f"  [{label}]  {method}  {url}")
    if body:
        print(f"  Body: {json.dumps(body)[:200]}")
    print(sep)

    try:
        if method == "GET":
            resp = requests.get(url, headers=headers, timeout=TIMEOUT)
        else:
            resp = requests.post(url, json=body, headers=headers, timeout=TIMEOUT)

        status_emoji = "✓" if resp.status_code < 300 else ("⚠" if resp.status_code < 500 else "✗")
        print(f"  {status_emoji}  HTTP {resp.status_code}  {resp.reason}")
        print(f"  Response headers: Content-Type={resp.headers.get('Content-Type','?')}")
        print(f"  Body:\n{textwrap.indent(_fmt(resp), '    ')}")

    except requests.exceptions.ConnectionError as e:
        print(f"  ✗  CONNECTION ERROR: {e}")
    except requests.exceptions.Timeout:
        print(f"  ✗  TIMEOUT after {TIMEOUT}s")
    except Exception as e:
        print(f"  ✗  {type(e).__name__}: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="Probe IBM watsonx Orchestrate API endpoints")
    parser.add_argument("--idea", default="A mobile app for tracking personal expenses")
    args = parser.parse_args()
    idea = args.idea

    print("=" * 72)
    print("  IBM watsonx Orchestrate — API Endpoint Probe")
    print("=" * 72)
    print(f"  BASE_URL    : {BASE_URL or '(NOT SET)'}")
    print(f"  INSTANCE_ID : {INSTANCE_ID or '(NOT SET)'}")
    print(f"  AGENT_ID    : {AGENT_ID or '(NOT SET)'}")
    print(f"  API_KEY     : {'SET (' + API_KEY[:6] + '…)' if API_KEY else '(NOT SET)'}")

    if not all([BASE_URL, API_KEY, INSTANCE_ID, AGENT_ID]):
        print("\n  ERROR: Missing required env vars. Check your .env file.")
        sys.exit(1)

    token = get_iam_token(API_KEY)

    print(f"\n[2/2] Probing {BASE_URL} with agent {AGENT_ID} …")

    # ── Candidate 0: list agents (verify instance is reachable) ──────────
    probe("0 – List agents",
          "GET", f"{BASE_URL}/v1/agents",
          token)

    # ── Candidate 1: GET agent by ID (does it exist?) ────────────────────
    probe("1 – Get agent by ID",
          "GET", f"{BASE_URL}/v1/agents/{AGENT_ID}",
          token)

    # ── Candidate 2: current impl — /v1/agents/{id}/chat ─────────────────
    probe("2 – /v1/agents/{id}/chat  (message_type)",
          "POST", f"{BASE_URL}/v1/agents/{AGENT_ID}/chat",
          token,
          body={
              "input": {
                  "message_type": "text",
                  "text": idea,
              },
          })

    # ── Candidate 3: /v1/agents/{id}/chat — plain text input ─────────────
    probe("3 – /v1/agents/{id}/chat  (plain text input)",
          "POST", f"{BASE_URL}/v1/agents/{AGENT_ID}/chat",
          token,
          body={"input": {"text": idea}})

    # ── Candidate 4: /v1/agents/{id}/chat — top-level message field ──────
    probe("4 – /v1/agents/{id}/chat  (top-level message)",
          "POST", f"{BASE_URL}/v1/agents/{AGENT_ID}/chat",
          token,
          body={"message": idea})

    # ── Candidate 5: /v2/agents/{id}/chat ────────────────────────────────
    probe("5 – /v2/agents/{id}/chat",
          "POST", f"{BASE_URL}/v2/agents/{AGENT_ID}/chat",
          token,
          body={
              "input": {"message_type": "text", "text": idea},
          })

    # ── Candidate 6: /v1/agents/{id}/runs ────────────────────────────────
    probe("6 – /v1/agents/{id}/runs",
          "POST", f"{BASE_URL}/v1/agents/{AGENT_ID}/runs",
          token,
          body={"input": {"text": idea}})

    # ── Candidate 7: /v1/agent/chat — agent_id in body ───────────────────
    probe("7 – /v1/agent/chat  (agent_id in body)",
          "POST", f"{BASE_URL}/v1/agent/chat",
          token,
          body={
              "agent_id": AGENT_ID,
              "input": {"text": idea},
          })

    # ── Candidate 8: /v1/chat — agent_id in body ─────────────────────────
    probe("8 – /v1/chat  (agent_id in body)",
          "POST", f"{BASE_URL}/v1/chat",
          token,
          body={
              "agent_id": AGENT_ID,
              "input": {"message_type": "text", "text": idea},
          })

    # ── Candidate 9: ZenML-style /ml/v1/deployments/{id}/text/generation ─
    probe("9 – /ml/v1/deployments/{id}/text/generation",
          "POST", f"{BASE_URL}/ml/v1/deployments/{AGENT_ID}/text/generation",
          token,
          body={
              "input": idea,
              "parameters": {"max_new_tokens": 1024},
          })

    # ── Candidate 10: no X-IBM-Instance-ID, check if it matters ──────────
    probe("10 – /v1/agents/{id}/chat (NO instance header)",
          "POST", f"{BASE_URL}/v1/agents/{AGENT_ID}/chat",
          token,
          body={"input": {"message_type": "text", "text": idea}},
          extra_headers={"X-IBM-Instance-ID": ""})   # send blank to override

    print("\n" + "=" * 72)
    print("  Probe complete. Look for HTTP 200 or HTTP 201 above.")
    print("  Copy the working candidate number and share it.")
    print("=" * 72 + "\n")


if __name__ == "__main__":
    main()
