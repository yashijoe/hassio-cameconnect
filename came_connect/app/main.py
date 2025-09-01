# -*- coding: utf-8 -*-
import base64
import hashlib
import json
import os
import secrets
from typing import Tuple, List, Dict, Any

import httpx
from fastapi import FastAPI, HTTPException

# ---- Config ----
CLIENT_ID = os.getenv("CAME_CONNECT_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("CAME_CONNECT_CLIENT_SECRET", "")
USERNAME = os.getenv("CAME_CONNECT_USERNAME", "")
PASSWORD = os.getenv("CAME_CONNECT_PASSWORD", "")

# Let's try both app.\* and beta.\*
API_BASE_CANDIDATES = [
    "https://app.cameconnect.net/api",
    "https://beta.cameconnect.net/api",
]

OAUTH_AUTH_CODE_SUFFIX = "/oauth/auth-code"
OAUTH_TOKEN_SUFFIX = "/oauth/token"

TOKEN_PATH = "/data/token.json"

app = FastAPI(title="Came Connect Proxy", version="0.2.0")

# ---- Utility ----
def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

def _pkce_pair() -> Tuple[str, str]:
    verifier = _b64url(secrets.token_bytes(32)).replace("-", "").replace("_", "")
    challenge = _b64url(hashlib.sha256(verifier.encode("ascii")).digest())
    return verifier, challenge

def _basic_auth(client_id: str, client_secret: str) -> str:
    raw = f"{client_id}:{client_secret}".encode("utf-8")
    return "Basic " + base64.b64encode(raw).decode("ascii")

def load_token() -> Dict[str, Any] | None:
    try:
        with open(TOKEN_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return None

def save_token(tok: Dict[str, Any]) -> None:
    try:
        with open(TOKEN_PATH, "w") as f:
            json.dump(tok, f)
    except Exception:
        pass

def token_valid(tok: Dict[str, Any] | None) -> bool:
    return bool(tok and tok.get("access_token"))

def fetch_token() -> Dict[str, Any]:
    if not all([CLIENT_ID, CLIENT_SECRET, USERNAME, PASSWORD]):
        raise HTTPException(status_code=500, detail="Config mancante (client/user/pass).")

    verifier, challenge = _pkce_pair()
    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
        "Authorization": _basic_auth(CLIENT_ID, CLIENT_SECRET),
    }

    # Let's try auth-code and token on both base URLs
    last_err = None
    for base in API_BASE_CANDIDATES:
        try:
            with httpx.Client(timeout=30.0, follow_redirects=True) as s:
                # 1) obtain authorization code
                # Note: Came requires these parameters/headers; username/password in the x-www-form-urlencoded body
                auth_code_body = (
                    f"grant_type=authorization_code"
                    f"&username={httpx.QueryParams({'u': USERNAME})['u']}"
                    f"&password={httpx.QueryParams({'p': PASSWORD})['p']}"
                    f"&client_id={httpx.QueryParams({'c': CLIENT_ID})['c']}"
                )
                params = {
                    "client_id": CLIENT_ID,
                    "response_type": "code",
                    "redirect_uri": "https://beta.cameconnect.net/role",
                    "state": secrets.token_urlsafe(16),
                    "nonce": secrets.token_urlsafe(8),
                    "code_challenge": challenge,
                    "code_challenge_method": "S256",
                }
                r = s.post(base + OAUTH_AUTH_CODE_SUFFIX, content=auth_code_body, headers=headers, params=params)
                if r.status_code != 200:
                    last_err = f"{base} auth-code {r.status_code}: {r.text}"
                    continue
                data = r.json()
                code = data.get("code") or data.get("authorization_code") or data.get("Code")
                if not code:
                    last_err = f"{base} auth-code: no code in response: {data}"
                    continue

                # 2) exchange the code for a token
                token_data = {
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": "https://beta.cameconnect.net/role",
                    "code_verifier": verifier,
                }
                tr = s.post(base + OAUTH_TOKEN_SUFFIX, data=token_data, headers=headers)
                if tr.status_code != 200:
                    last_err = f"{base} token {tr.status_code}: {tr.text}"
                    continue

                tok = tr.json()
                tok["_base"] = base  # let's remember which base worked
                save_token(tok)
                return tok
        except Exception as e:
            last_err = f"{base} exception: {e}"

    raise HTTPException(status_code=502, detail=f"OAuth failed: {last_err}")

def ensure_token() -> Tuple[str, str]:
    tok = load_token()
    if not token_valid(tok):
        tok = fetch_token()
    return tok["access_token"], tok.get("_base") or API_BASE_CANDIDATES[0]


def _request_with_refresh(method: str, url: str, payload=None):
    """
    Esegue una richiesta con bearer token.
    Se riceve 401 (Expired token), rinnova il token e riprova una volta.
    Ritorna l'oggetto httpx.Response.
    """
    access, _ = ensure_token()
    headers = {"Authorization": f"Bearer {access}", "Accept": "application/json"}

    with httpx.Client(timeout=30.0) as s:
        if method.upper() == "POST":
            r = s.post(url, headers=headers, json=payload)
        else:
            r = s.get(url, headers=headers)

        if r.status_code == 401:
            # expired token: let's log in again and retry
            fetch_token()
            access, _ = ensure_token()
            headers["Authorization"] = f"Bearer {access}"
            if method.upper() == "POST":
                r = s.post(url, headers=headers, json=payload)
            else:
                r = s.get(url, headers=headers)

    return r

def _try_command_requests(access: str, base: str, device_id: int, command_id: int) -> Dict[str, Any]:
    """
    Prova varie combinazioni di endpoint/metodo come fa la webapp Came:
    - POST /automations/{device}/commands/{cmd}
    - POST /devices/{device}/commands/{cmd}
    - GET  /devices/{device}/command/{cmd}
    """
    candidates = [
        ("POST", f"{base}/automations/{device_id}/commands/{command_id}", None),
        ("POST", f"{base}/devices/{device_id}/commands/{command_id}", None),
        ("GET",  f"{base}/devices/{device_id}/command/{command_id}", None),
    ]
    last = None
    for method, url, payload in candidates:
        try:
            r = _request_with_refresh(method, url, payload)
            if r.status_code in (200, 202, 204):
                return {"ok": True, "method": method, "url": url, "status": r.status_code}
            last = {"ok": False, "method": method, "url": url, "status": r.status_code, "body": r.text}
        except Exception as e:
            last = {"ok": False, "method": method, "url": url, "error": str(e)}
    return last or {"ok": False, "error": "unknown"}

# ---- API ----
@app.get("/health")
def health():
    return {"ok": True}

@app.get("/devices/{device_id}/commands")
def list_commands(device_id: int):
    # list of commands with auto-refresh of the token
    access, base = ensure_token()
    urls = [
        f"{base}/automations/{device_id}/commands",
        f"{base}/devices/{device_id}/commands",
    ]
    last = None
    for u in urls:
        r = _request_with_refresh("GET", u)
        if r.status_code == 200:
            try:
                return {"ok": True, "base": base, "url": u, "data": r.json()}
            except Exception:
                return {"ok": True, "base": base, "url": u, "raw": r.text}
        last = {"status": r.status_code, "url": u, "body": r.text}
    raise HTTPException(status_code=502, detail={"message": "no commands endpoint worked", "last": last})

@app.get("/devices/{device_id}/status")
def device_status(device_id: int):
    """
    Normalized gate status for HA.
    - state: open | closed | opening | closing | stopped | moving | unknown
    - position: 0..100 (best effort)
    - moving: bool
    - direction: opening | closing | stopped | unknown
    - online, updated_at, raw
    """
    access, base = ensure_token()
    headers = {"Authorization": f"Bearer {access}", "Accept": "application/json"}

    url = f"{base}/automations/{device_id}/status"
    r = _request_with_refresh("GET", url)
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail={"message": "status fetch failed", "status": r.status_code, "body": r.text})
    data = r.json()

    ok = bool(data.get("Success"))
    payload = data.get("Data") or {}
    online = bool(payload.get("Online", True))
    states = payload.get("States") or []

    # index by CommandId
    by_cmd = {e.get("CommandId"): e for e in states if isinstance(e, dict)}

    # ZM3 codes observed on CommandId 1
    CODE_MAP = {
        16: "open",
        17: "closed",
        19: "stopped",
        32: "opening",
        33: "closing",
    }

    code = None
    pos_entry = by_cmd.get(1)
    if pos_entry and isinstance(pos_entry.get("Data"), list) and len(pos_entry["Data"]) >= 1:
        try:
            code = int(pos_entry["Data"][0])
        except Exception:
            code = None

    # Optional moving flag on CommandId 3
    moving_flag = False
    mv_entry = by_cmd.get(3)
    if mv_entry and isinstance(mv_entry.get("Data"), list) and len(mv_entry["Data"]) >= 1:
        try:
            moving_flag = int(mv_entry["Data"][0]) == 1
        except Exception:
            moving_flag = False

    # Derive state
    state = CODE_MAP.get(code, "unknown")
    # If we have no semantic state but flag says moving
    if state == "unknown" and moving_flag:
        state = "moving"

    # Derive direction
    if state in ("opening", "closing"):
        direction = state
    elif state == "stopped":
        direction = "stopped"
    else:
        direction = "unknown"

    # Best-effort position
    if state == "open":
        position = 100
    elif state == "closed":
        position = 0
    else:
        position = None

    # updated_at
    timestamps = []
    for e in (pos_entry, mv_entry):
        if e and e.get("UpdatedAt"):
            timestamps.append(e["UpdatedAt"])
    updated_at = max(timestamps) if timestamps else payload.get("ConfiguredLastUpdate")

    return {
        "ok": ok,
        "base": base,
        "url": url,
        "state": state,
        "position": position,
        "moving": state in ("opening", "closing") or moving_flag,
        "direction": direction,
        "online": online,
        "raw_code": code,
        "updated_at": updated_at,
        "raw": data
    }

@app.get("/devices/{device_id}/command/{command_id}")
def exec_command(device_id: int, command_id: int):
    access, base = ensure_token()
    res = _try_command_requests(access, base, device_id, command_id)
    if res.get("ok"):
        return {"success": True, "used": {"method": res["method"], "url": res["url"], "status": res["status"]}}
    raise HTTPException(status_code=502, detail=res)

@app.get("/debug/token")
def debug_token():
    access, base = ensure_token()
    return {"ok": True, "base": base, "access_token_present": bool(access)}

@app.get("/debug/token_detail")
def token_detail():
    access, base = ensure_token()
    import time, json, base64
    def _jwt_payload(jwt: str):
        try:
            parts = jwt.split(".")
            pad = "=" * (-len(parts[1]) % 4)
            return json.loads(base64.urlsafe_b64decode((parts[1] + pad).encode()).decode("utf-8"))
        except Exception:
            return None
    payload = _jwt_payload(access) if access else None
    exp = payload.get("exp") if payload else None
    now = int(time.time())
    return {
        "ok": bool(access),
        "base": base,
        "has_payload": bool(payload),
        "exp": exp,
        "expires_in_s": (exp - now) if exp else None
    }

@app.get("/debug/fullscan/{device_id}")
def debug_fullscan(device_id: int, truncate: int = 4000, find: str | None = None):
    """
    Probe many possible Came endpoints for a given device_id (and its RootId if available).
    Tries both /automations and /devices with common suffixes: status, commands, inputs, io,
    maintenance, statistics, diagnostics, usage, history.
    Returns HTTP status and body/json for each URL.
    Query params:
      - truncate: max body chars to return (default 4000)
      - find: optional substring to search in response bodies (adds 'found': true)
    """
    access, base = ensure_token()

    def _safe_get(url: str):
        try:
            r = _request_with_refresh("GET", url)
            body = r.text
            hit = (find in body) if (find and body) else False
            out = {"url": url, "status": r.status_code, "found": hit}
            # try parse json
            try:
                out["json"] = r.json()
                out["body"] = None
            except Exception:
                # keep (possibly truncated) text body
                if body and len(body) > truncate:
                    body = body[:truncate] + "...(truncated)"
                out["body"] = body
            return out
        except Exception as e:
            return {"url": url, "error": str(e)}

    # collect endpoints for device_id and (if present) its RootId
    ids = [int(device_id)]
    # try to discover RootId from /devices/{id}
    try:
        url_dev = f"{base}/devices/{device_id}"
        rdev = _request_with_refresh("GET", url_dev)
        if rdev.status_code == 200:
            j = rdev.json()
            root_id = (((j or {}).get("Data") or {}).get("RootId"))
            if isinstance(root_id, int) and root_id not in ids:
                ids.append(root_id)
    except Exception:
        root_id = None

    # paths to try
    prefixes = ["automations", "devices"]
    suffixes = ["", "/status", "/commands", "/inputs", "/io",
                "/maintenance", "/statistics", "/diagnostics", "/usage", "/history"]

    urls = []
    for did in ids:
        for p in prefixes:
            for s in suffixes:
                urls.append(f"{base}/{p}/{did}{s}")

    # de-dup just in case
    urls = list(dict.fromkeys(urls))

    results = [_safe_get(u) for u in urls]

    return {
        "ok": True,
        "base": base,
        "device_id": int(device_id),
        "root_id": root_id if 'root_id' in locals() else None,
        "tested": len(urls),
        "truncate": truncate,
        "find": find,
        "results": results
    }