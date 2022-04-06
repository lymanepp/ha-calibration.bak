"""Support for calibration sensor."""
from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_UNIT_OF_MEASUREMENT,
    CONF_ATTRIBUTE,
    CONF_DEVICE_CLASS,
    CONF_FRIENDLY_NAME,
    CONF_SOURCE,
    CONF_UNIQUE_ID,
    CONF_UNIT_OF_MEASUREMENT,
    STATE_UNKNOWN,
)
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import (
    ATTR_COEFFICIENTS,
    ATTR_SOURCE,
    ATTR_SOURCE_ATTRIBUTE,
    ATTR_SOURCE_VALUE,
    CONF_CALIBRATION,
    CONF_POLYNOMIAL,
    CONF_PRECISION,
    DATA_CALIBRATION,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,  # pylint: disable=unused-argument
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the Calibration sensor."""
    if discovery_info is None:
        return

    calibration = discovery_info[CONF_CALIBRATION]
    conf = hass.data[DATA_CALIBRATION][calibration]

    unique_id = conf.get(CONF_UNIQUE_ID) or calibration
    name = conf.get(CONF_FRIENDLY_NAME) or calibration.replace("_", " ").title()
    source = conf[CONF_SOURCE]
    attribute = conf.get(CONF_ATTRIBUTE)

    async_add_entities(
        [
            CalibrationSensor(
                unique_id,
                name,
                source,
                attribute,
                conf[CONF_PRECISION],
                conf[CONF_POLYNOMIAL],
                conf.get(CONF_DEVICE_CLASS),
                conf.get(CONF_UNIT_OF_MEASUREMENT),
            )
        ]
    )


class CalibrationSensor(SensorEntity):  # pylint: disable=too-many-instance-attributes
    """Representation of a Calibration sensor."""

    def __init__(
        self,
        unique_id: str,
        name: str,
        source: str,
        attribute: str | None,
        precision: int,
        polynomial,
        device_class: str,
        unit_of_measurement: str,
    ):  # pylint: disable=too-many-arguments
        """Initialize the Calibration sensor."""
        self._attr_unique_id = unique_id
        self._attr_name = name
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit_of_measurement
        self._attr_should_poll = False

        self._source_entity_id = source
        self._source_attribute = attribute
        self._precision = precision
        self._poly = polynomial

        self._attr_extra_state_attributes = {
            ATTR_COEFFICIENTS: polynomial.coefficients.tolist(),
            ATTR_SOURCE: source,
            ATTR_SOURCE_ATTRIBUTE: attribute,
            ATTR_SOURCE_VALUE: None,
        }
        if not attribute:
            del self._attr_extra_state_attributes[ATTR_SOURCE_ATTRIBUTE]

    async def async_added_to_hass(self) -> None:
        """Handle added to Hass."""
        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                [self._source_entity_id],
                self._async_calibration_sensor_state_listener,
            )
        )

    @callback
    def _async_calibration_sensor_state_listener(self, event: Event) -> None:
        """Handle sensor state changes."""
        if (new_state := event.data.get("new_state")) is None:
            return

        if self._source_attribute is None:
            # Initialize on first state change if not configured
            if self._attr_device_class is None:
                self._attr_device_class = new_state.attributes.get(ATTR_DEVICE_CLASS)
            if self._attr_native_unit_of_measurement is None:
                self._attr_native_unit_of_measurement = new_state.attributes.get(
                    ATTR_UNIT_OF_MEASUREMENT
                )

        try:
            source_value = (
                float(new_state.attributes.get(self._source_attribute))
                if self._source_attribute
                else float(new_state.state)
                if new_state.state != STATE_UNKNOWN
                else None
            )
            self._attr_native_value = round(self._poly(source_value), self._precision)
            self._attr_extra_state_attributes[ATTR_SOURCE_VALUE] = source_value
        except (ValueError, TypeError):
            self._attr_native_value = None
            if self._source_attribute:
                _LOGGER.warning(
                    "%s attribute %s is not a number",
                    self._source_entity_id,
                    self._source_attribute,
                )
            else:
                _LOGGER.warning("%s state is not a number", self._source_entity_id)

        self.async_write_ha_state()
