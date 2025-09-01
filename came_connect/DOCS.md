# Came Connect

> If the links don’t open, replace `homeassistant` with the IP of your HA (e.g. `http://192.168.1.50:9002/...`).

## Health check
- http://homeassistant:9002/health

## Gate status (normalized)
- http://homeassistant:9002/devices/DEVICE-ID/status  
  Returns: `state` (`open`/`closed`/`opening`/`closing`/`stopped`/`unknown`), `position`, `moving`, `direction`, `raw_code`, `updated_at`, `online`, `raw`.

## Command execution _(clicking will actually execute the command!)_
- **Open** http://homeassistant:9002/devices/DEVICE-ID/command/2  
- **Partial opening** http://homeassistant:9002/devices/DEVICE-ID/command/4  
- **Close** http://homeassistant:9002/devices/DEVICE-ID/command/5  
- **Toggle (open/close)** http://homeassistant:9002/devices/DEVICE-ID/command/8  
- **Sequential** http://homeassistant:9002/devices/DEVICE-ID/command/9  
- **Stop** http://homeassistant:9002/devices/DEVICE-ID/command/129

## Current Token / Base
- http://homeassistant:9002/debug/token  
- http://homeassistant:9002/debug/token_detail

## Command ping with auto-detection of URL/method
- http://homeassistant:9002/debug/ping/DEVICE-ID/`<COMMAND_ID>`
