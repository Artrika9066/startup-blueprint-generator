"""
orchestrate_client.py – Low-level HTTP client for IBM watsonx Orchestrate.

Endpoint
--------
POST /v1/agents/{agent_id}/chat
    Tries three request body shapes in order and returns the first that
    succeeds (HTTP 2xx).  If all fail, raises a detailed APIError that
    includes the HTTP status and the full response body from IBM.

Authentication
--------------
  Authorization: Bearer <IAM-token>
  X-IBM-Instance-ID: <instance-uuid>

Reference:
  https://developer.ibm.com/watson/watsonx-orchestrate-developer-hub/
"""

from __future__ import annotations

import json
import logging
from typing import Any

import requests

from .auth import IAMTokenManager

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Custom exception — carries the raw IBM error body
# ─────────────────────────────────────────────────────────────────────────────

class APIError(RuntimeError):
    """Raised when every candidate request body variant returns an HTTP error."""
    def __init__(self, agent_id: str, attempts: list[dict]) -> None:
        self.agent_id = agent_id
        self.attempts = attempts   # list of {"body_variant": n, "status": n, "body": str}
        lines = [f"All request variants failed for agent {agent_id}:"]
        for a in attempts:
            lines.append(
                f"  variant {a['body_variant']}  HTTP {a['status']}: {a['body'][:400]}"
            )
        super().__init__("\n".join(lines))


# ─────────────────────────────────────────────────────────────────────────────
# Client
# ─────────────────────────────────────────────────────────────────────────────

class OrchestrateClient:
    """
    Thin wrapper around the watsonx Orchestrate Agent REST API.

    Parameters
    ----------
    base_url        : Root URL, e.g. https://api.eu-gb.watson-orchestrate.cloud.ibm.com
    api_key         : IBM Cloud API key (exchanges for an IAM bearer token).
    instance_id     : Orchestrate instance UUID (sent as X-IBM-Instance-ID).
    timeout_seconds : HTTP socket timeout per request.
    """

    # Candidate request body shapes tried in order.
    # The first one that gets an HTTP 2xx wins; all others are logged and skipped.
    _BODY_VARIANTS: list[str] = [
        "message_type",   # {"input": {"message_type": "text", "text": "…"}}
        "plain_text",     # {"input": {"text": "…"}}
        "top_message",    # {"message": "…"}
    ]

    def __init__(
        self,
        base_url: str,
        api_key: str,
        instance_id: str,
        timeout_seconds: int = 120,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._instance_id = instance_id
        self._timeout = timeout_seconds
        self._token_mgr = IAMTokenManager(api_key)
        # Cache the first working body variant so we don't retry on every call
        self._working_variant: str | None = None

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def chat(
        self,
        agent_id: str,
        message: str,
        *,
        additional_context: dict[str, Any] | None = None,
    ) -> str:
        """
        Send *message* to *agent_id* and return the response text.

        Tries multiple request body shapes and returns the first successful
        response.  If none succeed, raises :class:`APIError` with the full
        HTTP status and response body for every attempt.

        Parameters
        ----------
        agent_id           : Bare UUID of the target agent.
        message            : The user prompt text.
        additional_context : Optional key/value pairs merged under ``"context"``.

        Returns
        -------
        Agent response as plain text.
        """
        url = f"{self._base_url}/v1/agents/{agent_id}/chat"
        failed: list[dict] = []

        # If a working variant was already discovered, try it first
        ordered = (
            [self._working_variant]
            + [v for v in self._BODY_VARIANTS if v != self._working_variant]
            if self._working_variant
            else self._BODY_VARIANTS
        )

        for variant in ordered:
            body = self._build_body(variant, message, additional_context)
            logger.info("POST %s  [variant=%s]", url, variant)
            logger.debug("Request body: %s", json.dumps(body))

            try:
                resp = requests.post(
                    url,
                    json=body,
                    headers=self._headers(),
                    timeout=self._timeout,
                )
            except requests.exceptions.RequestException as exc:
                logger.error("Network error on variant %s: %s", variant, exc)
                failed.append({"body_variant": variant, "status": 0, "body": str(exc)})
                continue

            # Always log the full response body at DEBUG level
            raw_body = self._safe_body_text(resp)
            logger.debug("HTTP %s  body: %s", resp.status_code, raw_body[:2000])

            if resp.status_code in (200, 201, 202):
                logger.info("  → HTTP %s — variant '%s' succeeded", resp.status_code, variant)
                self._working_variant = variant   # remember for next call
                try:
                    data = resp.json()
                except Exception:
                    return raw_body   # non-JSON 2xx — return raw text

                text = self._extract_text(data)
                if text:
                    return text
                # 2xx but couldn't find text — return the entire JSON as a string
                logger.warning("Received 2xx but could not extract text; returning raw response")
                return raw_body

            # Non-2xx — log the full error body and try next variant
            logger.warning(
                "  → HTTP %s on variant '%s': %s",
                resp.status_code, variant, raw_body[:500],
            )
            failed.append({
                "body_variant": variant,
                "status":       resp.status_code,
                "body":         raw_body,
            })

        raise APIError(agent_id, failed)

    # ------------------------------------------------------------------ #
    # Private helpers                                                      #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _build_body(
        variant: str,
        message: str,
        additional_context: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Return the request body dict for the given *variant* name."""
        if variant == "message_type":
            body: dict[str, Any] = {
                "input": {
                    "message_type": "text",
                    "text": message,
                },
            }
        elif variant == "plain_text":
            body = {
                "input": {"text": message},
            }
        elif variant == "top_message":
            body = {"message": message}
        else:
            body = {"input": {"text": message}}

        if additional_context:
            body["context"] = additional_context
        return body

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization":     f"Bearer {self._token_mgr.token}",
            "Content-Type":      "application/json",
            "Accept":            "application/json",
            "X-IBM-Instance-ID": self._instance_id,
        }

    @staticmethod
    def _safe_body_text(resp: requests.Response) -> str:
        """Return response body as text without raising."""
        try:
            return json.dumps(resp.json(), ensure_ascii=False)
        except Exception:
            return resp.text or ""

    @staticmethod
    def _extract_text(response: dict) -> str:
        """
        Walk known watsonx Orchestrate response shapes to find the text payload.

        Observed shapes
        ---------------
        {"output": {"text": "..."}}
        {"output": {"generic": [{"text": "..."}]}}
        {"output": {"generic": [{"response_type": "text", "text": "..."}]}}
        {"result": {"text": "..."}}
        {"message": {"text": "..."}}
        {"response": "..."}
        {"text": "..."}
        {"choices": [{"message": {"content": "..."}}]}   ← OpenAI-compat shape
        """
        # output.text  or  output.content
        output = response.get("output")
        if isinstance(output, dict):
            text = output.get("text") or output.get("content")
            if text:
                return str(text)
            # output.generic list
            generic = output.get("generic")
            if isinstance(generic, list):
                parts = [
                    item.get("text") or item.get("content") or ""
                    for item in generic
                    if isinstance(item, dict)
                ]
                combined = "\n".join(p for p in parts if p)
                if combined:
                    return combined

        # result.text / message.text
        for key in ("result", "message"):
            nested = response.get(key)
            if isinstance(nested, dict):
                text = nested.get("text") or nested.get("content")
                if text:
                    return str(text)

        # OpenAI-compat: choices[0].message.content
        choices = response.get("choices")
        if isinstance(choices, list) and choices:
            msg = choices[0].get("message") or {}
            if isinstance(msg, dict) and msg.get("content"):
                return str(msg["content"])

        # Flat top-level fields
        for key in ("response", "text", "content", "answer", "generated_text"):
            val = response.get(key)
            if val and isinstance(val, str):
                return val

        return ""
