import base64
import os
from typing import Any

import httpx

from .constants import CLIENT_MAX_PAGES

ENV_TO_BASE_URL = {
    "demo": "https://demo-api.ramp.com/developer/v1",
    "prd": "https://api.ramp.com/developer/v1",
}


def get_access_token_with_client_credentials(base_url: str, scopes: list[str]) -> str:
    client_id, client_secret = (
        os.getenv("RAMP_CLIENT_ID"),
        os.getenv("RAMP_CLIENT_SECRET"),
    )
    headers = {
        "Accept": "application/json",
        "Authorization": f"Basic {base64.b64encode(f'{client_id}:{client_secret}'.encode()).decode()}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    payload = {
        "grant_type": "client_credentials",
        "scope": " ".join(scopes),
    }

    response = httpx.post(
        f"{base_url}/token",
        headers=headers,
        data=payload,
    )
    response.raise_for_status()

    return response.json()["access_token"]


class RampAsyncClient:
    """
    Lightweight wrapper around Ramp's Developer API
    """

    def connect(self, scopes: list[str]):
        if not self._access_token:
            self._access_token = get_access_token_with_client_credentials(
                self._base_url,
                scopes,
            )
        self.client = httpx.AsyncClient(
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self._access_token}",
                "Content-Type": "application/json",
                "User-Agent": "Ramp-MCP/0.0.1",
            }
        )

    def __init__(self):
        env = os.getenv("RAMP_ENV", "demo")
        if env not in ENV_TO_BASE_URL:
            raise ValueError(f"Invalid Ramp environment: {env}")
        self._base_url = ENV_TO_BASE_URL[env]
        self._access_token = None
        self.client = None

    async def paginate_list_endpoint(
        self,
        path: str,
        params: dict[str, Any],
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """
        GET all pages of a list endpoint
        """
        results = []
        _url = f"{self._base_url}{path}"
        i = 1
        while _url is not None:
            if i > CLIENT_MAX_PAGES:
                raise Exception("Too many pages, try to filter more results out.")
            response = await self.client.get(
                _url,
                params=params | kwargs if not results else None,
            )
            response.raise_for_status()
            res = response.json()
            results.extend(res["data"])

            _url = res["page"]["next"]
            i += 1
        return results
