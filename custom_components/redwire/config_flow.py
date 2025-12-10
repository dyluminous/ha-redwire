from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import DOMAIN, CONF_TOPIC_SETPOINT, CONF_TOPIC_STATE, CONF_TEMPERATURE_SENSOR

class RedwireConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        errors = {}
        if user_input is not None:
            topic_set = user_input.get(CONF_TOPIC_SETPOINT)
            topic_state = user_input.get(CONF_TOPIC_STATE)
            temp_sensor = user_input.get(CONF_TEMPERATURE_SENSOR)
            if not topic_set or not topic_state or not temp_sensor:
                errors["base"] = "missing_topics"
            else:
                return self.async_create_entry(title="Redwire Heater", data=user_input)

        data_schema = vol.Schema({
            vol.Required(CONF_TOPIC_SETPOINT, default="kitchen/heater/controller/setpoint"): str,
            vol.Required(CONF_TOPIC_STATE, default="kitchen/heater/controller/state"): str,
            vol.Required(CONF_TEMPERATURE_SENSOR): selector.selector({
                "entity": {
                    "domain": "sensor",
                }
            }),
        })
        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)
