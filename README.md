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

### `configuration.yaml`
```yaml
sensor: !include sensors.yaml
rest_command: !include rest_command.yaml
cover: !include cover.yaml
```

### `rest_command.yaml`
Replace `DEVICE-ID` with your Came device ID and adjust the host/port if needed (`homeassistant`, `homeassistant.local`, or the IP of your HA instance).

```yaml
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



### `sensors.yaml`
Replace `DEVICE-ID` with your Came device ID and adjust the host/port if needed (`homeassistant`, `homeassistant.local`, or the IP of your HA instance).

```yaml
- platform: rest
  name: Came
  unique_id: came
  icon: mdi:gate
  resource: "http://homeassistant:9002/devices/DEVICE-ID/status"
  method: GET
  value_template: "{{ value_json.state | default('unknown') }}"
  scan_interval: 5
  json_attributes:
    - position
    - moving
    - direction
    - online
    - raw_code
    - updated_at
    - maneuvers
```

### `cover.yaml`
```yaml
- platform: template
  covers:
    gate:
      friendly_name: "Came"
      device_class: gate
      icon_template: "mdi:gate"
      availability_template: >
        {{ state_attr('sensor.came', 'online') is not false }}

      # State mapping
      value_template: >-
        {% set s = states('sensor.came')|lower %}
        {% if s in ['open','aperto','apertura','parziale'] %}
          open
        {% elif s in ['closing','chiusura'] %}
          closing
        {% elif s in ['opening','apertura_in_corso'] %}
          opening
        {% else %}
          closed
        {% endif %}

      # Optional: position if provided by the device (0-100)
      position_template: >-
        {{ state_attr('sensor.came', 'position') | int(0) }}

      # Expose maneuvers counter as attribute
      attribute_templates:
        maneuvers: "{{ state_attr('sensor.came', 'maneuvers') }}"

      open_cover:
        service: rest_command.came_open
      close_cover:
        service: rest_command.came_close
      stop_cover:
        service: rest_command.came_stop

      # Optional extra commands (can be triggered from automations)
      extra_buttons:
        - name: "Partial open"
          icon: mdi:gate-open
          service: rest_command.came_partial_open
        - name: "Toggle"
          icon: mdi:swap-horizontal
          service: rest_command.came_toggle
        - name: "Sequential"
          icon: mdi:ray-start-end
          service: rest_command.came_sequential
```
