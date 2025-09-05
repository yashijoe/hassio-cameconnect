# Came Connect Add-on for Home Assistant

(Thanks to https://github.com/jasonmadigan/came-connect)

This add-on runs a local REST proxy that connects to the Came Connect cloud and exposes your gate as simple HTTP endpoints inside your Home Assistant network.  
It manages login, token refresh, and provides normalized status and command endpoints for your Came gate.

---

## Credentials required
You need to provide the same credentials you use in the Came Connect app:
- **Client ID** and **Client Secret** (from the Came Connect web app / developer portal)
- **Username** (your Came Connect account user)
- **Password** (your Came Connect account password)

These values are entered in the add-on **Configuration** page in Home Assistant.

---

## How to find your Client ID and Client Secret

Came Connect uses OAuth2 to authenticate.  
When you log in from the web portal, the browser downloads a JavaScript file that contains the application’s **Client ID** and **Client Secret**.

To find them:

1. Open [https://www.cameconnect.net/login](https://www.cameconnect.net/login) in your browser.
2. Log in with your Came Connect account (username and password).
3. After logging in, open the browser **Developer Tools** (usually F12).
4. Go to the **Network** or **Sources** tab.
5. Look for a large JavaScript file (e.g. `main.*.js`).
6. Open it and search (Ctrl+F) for the keywords:
   - `clientId`
   - `clientSecret`
7. Copy these two values and paste them into the add-on **Configuration** in Home Assistant.

⚠️ Important: keep Client ID and Client Secret private. Do not share them.

## How to find your your Device ID
Each Came gate registered in your account has a unique **Device ID**.

- Log in to [https://www.cameconnect.net](https://www.cameconnect.net), open your device page and check the URL:  
  e.g. `https://www.cameconnect.net/home/devices/214319` → here the Device ID is `214319`.

  
## Home Assistant configuration

You can integrate the add-on endpoints directly in Home Assistant by adding the following `rest_command` block to your `configuration.yaml`.  
Replace `DEVICE-ID` with your actual Came device ID.

```yaml
rest_command:
  came_health:
    url: "http://homeassistant:9002/health"
    method: GET

  came_status:
    url: "http://homeassistant:9002/devices/DEVICE-ID/status"
    method: GET

  came_open:
    url: "http://homeassistant:9002/devices/DEVICE-ID/command/2"
    method: POST

  came_open_partial:
    url: "http://homeassistant:9002/devices/DEVICE-ID/command/4"
    method: POST

  came_close:
    url: "http://homeassistant:9002/devices/DEVICE-ID/command/5"
    method: POST

  came_toggle:
    url: "http://homeassistant:9002/devices/DEVICE-ID/command/8"
    method: POST

  came_sequential:
    url: "http://homeassistant:9002/devices/DEVICE-ID/command/9"
    method: POST

  came_stop:
    url: "http://homeassistant:9002/devices/DEVICE-ID/command/129"
    method: POST

  came_token:
    url: "http://homeassistant:9002/debug/token"
    method: GET

  came_token_detail:
    url: "http://homeassistant:9002/debug/token_detail"
    method: GET

  came_ping:
    url: "http://homeassistant:9002/debug/ping/DEVICE-ID/{{ command_id }}"
    method: GET

```

### Command reference

| YAML command        | Description                                                                 |
|---------------------|-----------------------------------------------------------------------------|
| `came_health`       | Checks if the add-on is running (`/health`).                                |
| `came_status`       | Retrieves the normalized gate status (`open`, `closed`, `opening`, `closing`, `stopped`, `unknown`). |
| `came_open`         | Sends the **Open** command to the gate.                                     |
| `came_open_partial` | Sends the **Partial opening** command to the gate.                          |
| `came_close`        | Sends the **Close** command to the gate.                                    |
| `came_toggle`       | Sends the **Toggle (open/close)** command to the gate.                      |
| `came_sequential`   | Sends the **Sequential** command to the gate.                               |
| `came_stop`         | Sends the **Stop** command to the gate.                                     |
| `came_token`        | Returns a simple check showing whether the authentication token is present. |
| `came_token_detail` | Returns detailed information about the token, including expiration time.    |
| `came_ping`         | Tests sending a command dynamically by passing a `command_id` variable.     |


