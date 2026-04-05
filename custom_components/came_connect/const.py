"""Constants for the Came Connect integration."""

DOMAIN = "came_connect"

CONF_CLIENT_ID = "client_id"
CONF_CLIENT_SECRET = "client_secret"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_DEVICE_ID = "device_id"
CONF_DEVICE_NAME = "device_name"

API_BASE_CANDIDATES = [
    "https://app.cameconnect.net/api",
    "https://beta.cameconnect.net/api",
]

OAUTH_AUTH_CODE_SUFFIX = "/oauth/auth-code"
OAUTH_TOKEN_SUFFIX = "/oauth/token"
OAUTH_REDIRECT_URI = "https://beta.cameconnect.net/role"

# ZM3 status codes (CommandId=1, Data[0])
CODE_MAP = {
    16: "open",
    17: "closed",
    19: "stopped",
    32: "opening",
    33: "closing",
}

# Gate commands
CMD_OPEN = 2
CMD_PARTIAL_OPEN = 4
CMD_CLOSE = 5
CMD_TOGGLE = 8
CMD_SEQUENTIAL = 9
CMD_STOP = 129

SCAN_INTERVAL_SECONDS = 30
