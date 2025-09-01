# Came Connect

> Se i link non si aprono, sostituisci `homeassistant` con IP del tuo HA (es. `http://192.168.1.50:9002/...`).

## Health check
- http://homeassistant:9002/health

## Stato cancello (normalizzato)
- http://homeassistant:9002/devices/215596/status  
  Restituisce: `state` (`open`/`closed`/`opening`/`closing`/`stopped`/`unknown`), `position`, `moving`, `direction`, `raw_code`, `updated_at`, `online`, `raw`.

## Esecuzione comandi _(cliccarli esegue davvero il comando!)_
- **Apri** http://homeassistant:9002/devices/215596/command/2  
- **Apertura parziale** http://homeassistant:9002/devices/215596/command/4  
- **Chiudi** http://homeassistant:9002/devices/215596/command/5  
- **Inverti (open/close)** http://homeassistant:9002/devices/215596/command/8  
- **Sequenziale** http://homeassistant:9002/devices/215596/command/9  
- **Stop** http://homeassistant:9002/devices/215596/command/129

## Token / Base correnti
- http://homeassistant:9002/debug/token  
- http://homeassistant:9002/debug/token_detail

## Ping comando con auto-rilevamento URL/metodo
- http://homeassistant:9002/debug/ping/215596/`<ID_COMANDO>`

