"""
auth.py – Obtain and cache an IBM IAM bearer token.

IBM watsonx Orchestrate uses IBM Cloud IAM authentication.
POST https://iam.cloud.ibm.com/identity/token
  grant_type=urn:ibm:params:oauth:grant-type:apikey
  apikey=<your-api-key>
"""

import time
import requests

IAM_TOKEN_URL = "https://iam.cloud.ibm.com/identity/token"
_TOKEN_BUFFER_SECONDS = 60   # refresh this many seconds before expiry


class IAMTokenManager:
    """Fetch and auto-refresh an IBM IAM access token."""

    def __init__(self, api_key: str, timeout: int = 30) -> None:
        self._api_key = api_key
        self._timeout = timeout
        self._access_token: str = ""
        self._expires_at: float = 0.0

    # ------------------------------------------------------------------ #
    # Public                                                               #
    # ------------------------------------------------------------------ #

    @property
    def token(self) -> str:
        """Return a valid bearer token, refreshing if necessary."""
        if self._is_expired():
            self._refresh()
        return self._access_token

    # ------------------------------------------------------------------ #
    # Private                                                              #
    # ------------------------------------------------------------------ #

    def _is_expired(self) -> bool:
        return time.time() >= (self._expires_at - _TOKEN_BUFFER_SECONDS)

    def _refresh(self) -> None:
        response = requests.post(
            IAM_TOKEN_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
                "apikey": self._api_key,
            },
            timeout=self._timeout,
        )
        response.raise_for_status()
        payload = response.json()
        self._access_token = payload["access_token"]
        # IBM IAM tokens carry their expiry as epoch seconds
        self._expires_at = float(payload.get("expiration", time.time() + 3600))
