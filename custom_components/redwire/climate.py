from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.components import mqtt
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    HVACMode,
    ClimateEntityFeature,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    DOMAIN,
    DEFAULT_NAME,
    CONF_TOPIC_SETPOINT,
    CONF_TOPIC_STATE,
    CONF_TEMPERATURE_SENSOR,
    MIN_TEMP,
    MAX_TEMP,
)

_LOGGER = logging.getLogger(__name__)

@dataclass
class RedwireState:
    target_temp: float | None = None
    is_on: bool = False


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    async_add_entities([RedwireClimate(hass, entry)])


class RedwireClimate(ClimateEntity):
    _attr_should_poll = False
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]
    _attr_icon = "mdi:hvac"
    # Show one decimal place for displayed temperatures
    _attr_precision = 0.1
    # Keep setpoint control to whole degrees
    _attr_target_temperature_step = 1

    def __init__(self, hass: HomeAssistant, entry):
        self.hass = hass
        self._entry = entry
        self._attr_name = DEFAULT_NAME
        self._attr_unique_id = entry.entry_id
        self._device_info = DeviceInfo(identifiers={(DOMAIN, entry.entry_id)}, name=DEFAULT_NAME)

        self._state = RedwireState(target_temp=None, is_on=False)
        # If no setpoint received yet, start with a sensible default so the UI shows the dial
        self._state.target_temp = MIN_TEMP
        # Keep HA's cached attr in sync so the UI shows the value in the center
        self._attr_target_temperature = float(self._state.target_temp)

        self._topic_setpoint: str = entry.data.get(CONF_TOPIC_SETPOINT)
        self._topic_state: str = entry.data.get(CONF_TOPIC_STATE)
        self._current_temperature: float | None = None
        # Start unavailable until we read a valid temperature
        self._attr_available = False
        self._temperature_sensor_entity_id: str = entry.data.get(CONF_TEMPERATURE_SENSOR)

    @property
    def device_info(self) -> DeviceInfo:
        return self._device_info

    @property
    def hvac_mode(self):
        return HVACMode.HEAT if self._state.is_on else HVACMode.OFF

    @property
    def supported_features(self) -> int:
        return (
            ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.TURN_ON
            | ClimateEntityFeature.TURN_OFF
        )

    @property
    def target_temperature(self):
        return self._attr_target_temperature

    @property
    def min_temp(self):
        return MIN_TEMP

    @property
    def max_temp(self):
        return MAX_TEMP

    @property
    def current_temperature(self):
        return self._current_temperature

    @property
    def available(self) -> bool:
        return getattr(self, "_attr_available", True)

    async def async_set_temperature(self, **kwargs):
        if (temp := kwargs.get(ATTR_TEMPERATURE)) is None:
            return
        try:
            temp_int = int(round(float(temp)))
        except (TypeError, ValueError):
            _LOGGER.warning("Invalid temperature provided: %s", temp)
            return
        if temp_int < MIN_TEMP or temp_int > MAX_TEMP:
            _LOGGER.warning("Temperature out of range %s not in [%s,%s]", temp_int, MIN_TEMP, MAX_TEMP)
            return
        await mqtt.async_publish(self.hass, self._topic_setpoint, str(temp_int), qos=1, retain=False)
        self._state.target_temp = temp_int
        self._attr_target_temperature = float(temp_int)
        self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode):
        if hvac_mode == HVACMode.OFF:
            payload = "0"
        elif hvac_mode == HVACMode.HEAT:
            payload = "1"
        else:
            return
        await mqtt.async_publish(self.hass, self._topic_state, payload, qos=1, retain=False)
        self._state.is_on = payload == "1"
        # Make sure a target temp exists so HA shows the control when heating
        if self._state.is_on and self._state.target_temp is None:
            self._state.target_temp = MIN_TEMP
        # Sync cached attr
        if self._state.target_temp is not None:
            self._attr_target_temperature = float(self._state.target_temp)
        self.async_write_ha_state()

    async def async_turn_on(self) -> None:
        await self.async_set_hvac_mode(HVACMode.HEAT)

    async def async_turn_off(self) -> None:
        await self.async_set_hvac_mode(HVACMode.OFF)

    async def async_added_to_hass(self):
        # Initialize from current sensor state so the card shows a value immediately
        initial = self.hass.states.get(self._temperature_sensor_entity_id)
        if initial is not None:
            try:
                self._current_temperature = float(initial.state)
                self._attr_available = True
            except (TypeError, ValueError):
                self._attr_available = False
        else:
            self._attr_available = False
        self.async_write_ha_state()

        @callback
        def _sensor_state_change(event):
            state = event.data.get("new_state")
            if not state:
                self._attr_available = False
                self.async_write_ha_state()
                return
            try:
                self._current_temperature = float(state.state)
                # Valid temperature -> entity available
                self._attr_available = True
            except (TypeError, ValueError):
                # Unknown/unavailable or non-float -> mark unavailable
                self._attr_available = False
                _LOGGER.debug("Temperature sensor state not a float: %s", state.state)
                return
            self.async_write_ha_state()

        async_track_state_change_event(
            self.hass,
            [self._temperature_sensor_entity_id],
            _sensor_state_change,
        )

        @callback
        def _handle_setpoint(msg):
            try:
                val = int(msg.payload)
            except ValueError:
                _LOGGER.warning("Invalid setpoint payload: %s", msg.payload)
                return
            if val < MIN_TEMP or val > MAX_TEMP:
                _LOGGER.warning("Setpoint out of range %s not in [%s,%s]", val, MIN_TEMP, MAX_TEMP)
                return
            self._state.target_temp = val
            self._attr_target_temperature = float(val)
            self.async_write_ha_state()

        @callback
        def _handle_state(msg):
            if msg.payload not in ("0", "1"):
                _LOGGER.warning("Invalid state payload: %s", msg.payload)
                return
            self._state.is_on = msg.payload == "1"
            self.async_write_ha_state()

        await mqtt.async_subscribe(self.hass, self._topic_setpoint, _handle_setpoint, qos=1)
        await mqtt.async_subscribe(self.hass, self._topic_state, _handle_state, qos=1)
