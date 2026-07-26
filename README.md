# Redwire MQTT Heater Controller

> Note to self: This repo has to public as my HA isn't configured to pull private repos... nothing secret in here anyway!

Home Assistant custom integration providing a climate entity that controls an MQTT heater controller.

## Install
- Add `https://github.com/dyluminous/ha-redwire` to HACS as a Custom Repository (Integration).
- Install via HACS and restart Home Assistant.

## Configure
- Add the Redwire integration in Home Assistant.
- Enter your MQTT setpoint and state topics.
- Choose your temperature sensor entity.

## MQTT Topics
- Setpoint: integer string 10–30 (e.g., `21`).
- State: "0" (OFF) or "1" (HEAT).

## License
MIT
