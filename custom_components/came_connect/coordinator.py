"""Data coordinator and API client for Came Connect."""
from __future__ import annotations

import base64
import hashlib
import logging
import secrets
import time
from datetime import timedelta
from typing import Any

import httpx

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    API_BASE_CANDIDATES,
    CODE_MAP,
    DOMAIN,
    OAUTH_AUTH_CODE_SUFFIX,
    OAUTH_REDIRECT_URI,
    OAUTH_TOKEN_SUFFIX,
    SCAN_INTERVAL_SECONDS,
)

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}_token"


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _pkce_pair() -> tuple[str, str]:
    verifier = _b64url(secrets.token_bytes(32)).replace("-", "").replace("_", "")
    challenge = _b64url(hashlib.sha256(verifier.encode("ascii")).digest())
    return verifier, challenge


def _basic_auth(client_id: str, client_secret: str) -> str:
    raw = f"{client_id}:{client_secret}".encode("utf-8")
    return "Basic " + base64.b64encode(raw).decode("ascii")


def _jwt_exp(jwt: str) -> int | None:
    try:
        parts = jwt.split(".")
        pad = "=" * (-len(parts[1]) % 4)
        import json
        payload = json.loads(base64.urlsafe_b64decode((parts[1] + pad).encode()).decode())
        return payload.get("exp")
    except Exception:
        return None


class CameConnectApiClient:
    """Low-level Came Connect API client with OAuth2 + PKCE."""

    def __init__(
        self,
        hass: HomeAssistant,
        client_id: str,
        client_secret: str,
        username: str,
        password: str,
    ) -> None:
        self._hass = hass
        self._client_id = client_id
        self._client_secret = client_secret
        self._username = username
        self._password = password
        self._store: Store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._token: dict[str, Any] | None = None

    async def _load_token(self) -> dict[str, Any] | None:
        if self._token:
            return self._token
        data = await self._store.async_load()
        self._token = data
        return data

    async def _save_token(self, tok: dict[str, Any]) -> None:
        self._token = tok
        await self._store.async_save(tok)

    def _token_expired(self, tok: dict[str, Any]) -> bool:
        exp = _jwt_exp(tok.get("access_token", ""))
        if exp is None:
            return False
        return time.time() >= exp - 60  # 60s margin

    async def _fetch_token(self) -> dict[str, Any]:
        """Perform OAuth2 authorization_code + PKCE flow."""
        verifier, challenge = _pkce_pair()
        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
            "Authorization": _basic_auth(self._client_id, self._client_secret),
        }
        auth_body = (
            f"grant_type=authorization_code"
            f"&username={httpx.QueryParams({'u': self._username})['u']}"
            f"&password={httpx.QueryParams({'p': self._password})['p']}"
            f"&client_id={httpx.QueryParams({'c': self._client_id})['c']}"
        )
        params = {
            "client_id": self._client_id,
            "response_type": "code",
            "redirect_uri": OAUTH_REDIRECT_URI,
            "state": secrets.token_urlsafe(16),
            "nonce": secrets.token_urlsafe(8),
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }

        last_err = None
        for base in API_BASE_CANDIDATES:
            try:
                async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                    r = await client.post(
                        base + OAUTH_AUTH_CODE_SUFFIX,
                        content=auth_body,
                        headers=headers,
                        params=params,
                    )
                    if r.status_code != 200:
                        last_err = f"{base} auth-code {r.status_code}: {r.text[:200]}"
                        continue

                    data = r.json()
                    code = data.get("code") or data.get("authorization_code") or data.get("Code")
                    if not code:
                        last_err = f"{base} auth-code: no code in response"
                        continue

                    tr = await client.post(
                        base + OAUTH_TOKEN_SUFFIX,
                        data={
                            "grant_type": "authorization_code",
                            "code": code,
                            "redirect_uri": OAUTH_REDIRECT_URI,
                            "code_verifier": verifier,
                        },
                        headers=headers,
                    )
                    if tr.status_code != 200:
                        last_err = f"{base} token {tr.status_code}: {tr.text[:200]}"
                        continue

                    tok = tr.json()
                    tok["_base"] = base
                    await self._save_token(tok)
                    _LOGGER.debug("Token fetched from %s", base)
                    return tok
            except Exception as exc:
                last_err = f"{base} exception: {exc}"

        raise ConfigEntryAuthFailed(f"OAuth failed: {last_err}")

    async def async_get_token(self) -> tuple[str, str]:
        """Return (access_token, api_base), refreshing if needed."""
        tok = await self._load_token()
        if not tok or not tok.get("access_token"):
            tok = await self._fetch_token()
        elif self._token_expired(tok):
            _LOGGER.debug("Token expired, re-authenticating")
            tok = await self._fetch_token()
        return tok["access_token"], tok.get("_base") or API_BASE_CANDIDATES[0]

    async def _request(self, method: str, url: str, payload: Any = None) -> httpx.Response:
        """Execute an authenticated request, retrying once on 401."""
        access, _ = await self.async_get_token()
        headers = {"Authorization": f"Bearer {access}", "Accept": "application/json"}

        async with httpx.AsyncClient(timeout=30.0) as client:
            if method.upper() == "POST":
                r = await client.post(url, headers=headers, json=payload)
            else:
                r = await client.get(url, headers=headers)

            if r.status_code == 401:
                _LOGGER.debug("401 received, re-authenticating")
                self._token = None
                tok = await self._fetch_token()
                headers["Authorization"] = f"Bearer {tok['access_token']}"
                if method.upper() == "POST":
                    r = await client.post(url, headers=headers, json=payload)
                else:
                    r = await client.get(url, headers=headers)

        return r

    async def async_validate_credentials(self) -> bool:
        """Test credentials by fetching a token. Raises ConfigEntryAuthFailed on failure."""
        self._token = None
        await self._fetch_token()
        return True

    async def async_list_devices(self) -> list[dict[str, Any]]:
        """Try to discover devices from the API."""
        _, base = await self.async_get_token()
        devices: list[dict[str, Any]] = []
        for url in [f"{base}/automations", f"{base}/devices"]:
            try:
                r = await self._request("GET", url)
                if r.status_code == 200:
                    j = r.json()
                    data = j.get("Data") or j.get("data") or j
                    if isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict):
                                dev_id = item.get("Id") or item.get("id")
                                dev_name = item.get("Name") or item.get("name") or str(dev_id)
                                if dev_id is not None:
                                    devices.append({"id": int(dev_id), "name": dev_name})
                        if devices:
                            return devices
            except Exception:
                pass
        return devices

    async def async_get_device_status(self, device_id: int) -> dict[str, Any]:
        """Fetch and normalize device status."""
        _, base = await self.async_get_token()
        url = f"{base}/automations/{device_id}/status"
        r = await self._request("GET", url)
        if r.status_code != 200:
            raise UpdateFailed(f"Status fetch failed ({r.status_code}) for device {device_id}")

        data = r.json()
        payload = data.get("Data") or {}
        online = bool(payload.get("Online", True))
        states = payload.get("States") or []

        by_cmd = {e.get("CommandId"): e for e in states if isinstance(e, dict)}

        code = None
        pos_entry = by_cmd.get(1)
        if pos_entry and isinstance(pos_entry.get("Data"), list) and len(pos_entry["Data"]) >= 1:
            try:
                code = int(pos_entry["Data"][0])
            except Exception:
                pass

        moving_flag = False
        mv_entry = by_cmd.get(3)
        if mv_entry and isinstance(mv_entry.get("Data"), list) and len(mv_entry["Data"]) >= 1:
            try:
                moving_flag = int(mv_entry["Data"][0]) == 1
            except Exception:
                pass

        state = CODE_MAP.get(code, "unknown")
        if state == "unknown" and moving_flag:
            state = "moving"

        if state in ("opening", "closing"):
            direction = state
        elif state == "stopped":
            direction = "stopped"
        else:
            direction = "unknown"

        if state == "open":
            position = 100
        elif state == "closed":
            position = 0
        else:
            position = None

        timestamps = []
        for e in (pos_entry, mv_entry):
            if e and e.get("UpdatedAt"):
                timestamps.append(e["UpdatedAt"])
        updated_at = max(timestamps) if timestamps else payload.get("ConfiguredLastUpdate")

        maneuvers = self._decode_maneuvers(states)

        return {
            "state": state,
            "position": position,
            "moving": state in ("opening", "closing") or moving_flag,
            "direction": direction,
            "online": online,
            "raw_code": code,
            "updated_at": updated_at,
            "maneuvers": maneuvers,
        }

    @staticmethod
    def _decode_maneuvers(states: list[dict]) -> int | None:
        state18 = next(
            (s for s in states if isinstance(s, dict) and s.get("CommandId") == 18), None
        )
        if not state18:
            return None
        d = state18.get("Data") or []
        if not (isinstance(d, list) and len(d) >= 8):
            return None
        try:
            return int(d[2]) * 256 + int(d[3]) + int(d[6]) * 256 + int(d[7])
        except Exception:
            return None

    async def async_send_command(self, device_id: int, command_id: int) -> bool:
        """Send a command to the device, trying multiple endpoint variants."""
        _, base = await self.async_get_token()
        candidates = [
            ("POST", f"{base}/automations/{device_id}/commands/{command_id}", None),
            ("POST", f"{base}/devices/{device_id}/commands/{command_id}", None),
            ("GET", f"{base}/devices/{device_id}/command/{command_id}", None),
        ]
        for method, url, payload in candidates:
            try:
                r = await self._request(method, url, payload)
                if r.status_code in (200, 202, 204):
                    _LOGGER.debug("Command %s sent via %s %s", command_id, method, url)
                    return True
            except Exception as exc:
                _LOGGER.debug("Command attempt failed (%s %s): %s", method, url, exc)
        _LOGGER.error("All command attempts failed for device %s command %s", device_id, command_id)
        return False


class CameConnectCoordinator(DataUpdateCoordinator):
    """Coordinator that polls Came Connect device status."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: CameConnectApiClient,
        device_id: int,
        device_name: str,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{device_id}",
            update_interval=timedelta(seconds=SCAN_INTERVAL_SECONDS),
        )
        self.client = client
        self.device_id = device_id
        self.device_name = device_name

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self.client.async_get_device_status(self.device_id)
        except ConfigEntryAuthFailed:
            raise
        except Exception as exc:
            raise UpdateFailed(f"Error fetching data for device {self.device_id}: {exc}") from exc
