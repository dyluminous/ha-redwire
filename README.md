# Redwire MQTT Heater Controller

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
