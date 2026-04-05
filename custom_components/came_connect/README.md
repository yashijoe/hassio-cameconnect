# Came Connect — HACS Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

Native Home Assistant integration for controlling **Came automated gates** via the Came Connect cloud service.

## Features

- **Cover entity** with `device_class: gate` — open, close, stop
- **Auto-discovery** of devices from the API (fallback to manual ID)
- **Token auto-refresh** — OAuth2 + PKCE, cached between restarts
- **Extra attributes**: direction, maneuver counter, raw status code, last update
- **Config Flow** — full UI setup, no YAML needed
- **Translations**: English and Italian

## Installation via HACS

1. In HACS → *Integrations* → click the **⋮ menu** → *Custom repositories*
2. Add `https://github.com/yashijoe/ha-cameconnect` with category **Integration**
3. Install **Came Connect**
4. Restart Home Assistant

## Manual Installation

Copy the `custom_components/came_connect` folder into your HA `config/custom_components/` directory and restart.

## Configuration

1. **Settings → Devices & Services → Add Integration → Came Connect**
2. Enter your Came Connect API credentials:
   - **Client ID** — OAuth client identifier
   - **Client Secret** — OAuth client secret
   - **Username** — your Came Connect account email
   - **Password** — your Came Connect account password
3. Select your gate from the discovered list, or enter the device ID manually

> Your credentials are available from the Came Connect developer portal or by inspecting the Came Connect mobile app traffic.

## Entity Attributes

| Attribute | Description |
|---|---|
| `direction` | `opening` / `closing` / `stopped` / `unknown` |
| `raw_code` | Raw ZM3 status code from the API |
| `maneuvers` | Gate cycle counter (useful for maintenance) |
| `updated_at` | Timestamp of last state change |
| `device_id` | Came Connect device identifier |

## Commands Reference

| Command ID | Action |
|---|---|
| 2 | Open |
| 4 | Partial open |
| 5 | Close |
| 8 | Toggle |
| 9 | Sequential |
| 129 | Stop |

## Requirements

- Home Assistant 2024.1+
- `httpx>=0.27.0` (installed automatically)

## License

MIT
