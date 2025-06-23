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
    if not client_id or not client_secret:
        raise ValueError("RAMP_CLIENT_ID and RAMP_CLIENT_SECRET must be set for client credentials flow")
    
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


def get_access_token_from_env() -> str:
    access_token = os.getenv("RAMP_ACCESS_TOKEN")
    if not access_token:
        raise ValueError("RAMP_ACCESS_TOKEN must be set for OAuth2 flow")
    return access_token


def determine_auth_method() -> str:
    has_client_credentials = bool(os.getenv("RAMP_CLIENT_ID") and os.getenv("RAMP_CLIENT_SECRET"))
    has_access_token = bool(os.getenv("RAMP_ACCESS_TOKEN"))
    
    if has_client_credentials and has_access_token:
        raise ValueError("Cannot use both client credentials and access token. Set either RAMP_CLIENT_ID/RAMP_CLIENT_SECRET or RAMP_ACCESS_TOKEN, not both")
    
    if has_client_credentials:
        return "client_credentials"
    elif has_access_token:
        return "oauth2_token"
    else:
        raise ValueError("Must set either RAMP_CLIENT_ID/RAMP_CLIENT_SECRET for client credentials flow or RAMP_ACCESS_TOKEN for OAuth2 flow")


class RampAsyncClient:
    """
    Lightweight wrapper around Ramp's Developer API
    """

    def connect(self, scopes: list[str]):
        if not self._access_token:
            auth_method = determine_auth_method()
            if auth_method == "client_credentials":
                self._access_token = get_access_token_with_client_credentials(
                    self._base_url,
                    scopes,
                )
            elif auth_method == "oauth2_token":
                self._access_token = get_access_token_from_env()
            
            # TODO: remove this
            print(f"Access token: {self._access_token}")
        
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
            try:
                response = await self.client.get(
                    _url,
                    params=params | kwargs if not results else None,
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401:
                    raise Exception("Authentication failed. Please check your access token or client credentials.")
                elif e.response.status_code == 403:
                    raise Exception("Access forbidden. Please ensure your token has the required scopes for this operation.")
                else:
                    raise
            
            res = response.json()
            results.extend(res["data"])

            _url = res["page"]["next"]
            i += 1
        return results
