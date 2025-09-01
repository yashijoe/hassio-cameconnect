# Came Connect Add-on for Home Assistant

(Thanks to https://github.com/jasonmadigan/came-connect)

This add-on runs a local REST proxy that connects to the Came Connect cloud and exposes your gate as simple HTTP endpoints inside your Home Assistant network.  
It manages login, token refresh, and provides normalized status and command endpoints for your Came gate.

---

## Credentials required
You need to provide the same credentials you use in the Came Connect app:
- **Client ID** and **Client Secret** (from the Came Connect web app / developer portal)
- **Username** (your Came Connect account email)
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

  
