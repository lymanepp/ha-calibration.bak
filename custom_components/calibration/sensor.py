"""Support for calibration sensor."""
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
from homeassistant.core import callback
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    CONF_CALIBRATION,
    CONF_POLYNOMIAL,
    CONF_PRECISION,
    DATA_CALIBRATION,
    DEFAULT_NAME,
)

_LOGGER = logging.getLogger(__name__)

ATTR_COEFFICIENTS = "coefficients"
ATTR_SOURCE = "source"
ATTR_SOURCE_ATTRIBUTE = "source_attribute"


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Calibration sensor."""
    if discovery_info is None:
        return

    calibration = discovery_info[CONF_CALIBRATION]
    conf = hass.data[DATA_CALIBRATION][calibration]

    source = conf[CONF_SOURCE]
    attribute = conf.get(CONF_ATTRIBUTE)
    name = conf.get(CONF_FRIENDLY_NAME)
    if not name:
        name = f"{DEFAULT_NAME} {source}"
        if attribute is not None:
            name = f"{name} {attribute}"

    async_add_entities(
        [
            CalibrationSensor(
                calibration,
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


class CalibrationSensor(SensorEntity):
    """Representation of a Calibration sensor."""

    def __init__(
        self,
        id,
        name,
        source,
        attribute,
        precision,
        polynomial,
        device_class,
        unit_of_measurement,
    ):
        """Initialize the Calibration sensor."""
        self._source_entity_id = source
        self._precision = precision
        self._source_attribute = attribute
        self._device_class = device_class
        self._unit_of_measurement = unit_of_measurement
        self._poly = polynomial
        self._coefficients = polynomial.coefficients.tolist()
        self._state = None
        self._unique_id = id
        self._entity_id = id
        self._name = name

    async def async_added_to_hass(self):
        """Handle added to Hass."""
        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                [self._source_entity_id],
                self._async_calibration_sensor_state_listener,
            )
        )

    @property
    def unique_id(self):
        """Return the unique id of this sensor."""
        return self._unique_id

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the sensor."""
        ret = {
            ATTR_SOURCE: self._source_entity_id,
            ATTR_COEFFICIENTS: self._coefficients,
        }
        if self._source_attribute:
            ret[ATTR_SOURCE_ATTRIBUTE] = self._source_attribute
        return ret

    @property
    def device_class(self):
        """Return the class of this entity."""
        return self._device_class

    @property
    def native_unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return self._unit_of_measurement

    @callback
    def _async_calibration_sensor_state_listener(self, event):
        """Handle sensor state changes."""
        if (new_state := event.data.get("new_state")) is None:
            return

        if self._source_attribute is None:
            if self._device_class is None:
                self._device_class = new_state.attributes.get(
                    ATTR_DEVICE_CLASS
                )
            if self._unit_of_measurement is None:
                self._unit_of_measurement = new_state.attributes.get(
                    ATTR_UNIT_OF_MEASUREMENT
                )

        try:
            if self._source_attribute:
                value = float(new_state.attributes.get(self._source_attribute))
            else:
                value = (
                    None if new_state.state == STATE_UNKNOWN else float(new_state.state)
                )
            self._state = round(self._poly(value), self._precision)

        except (ValueError, TypeError):
            self._state = None
            if self._source_attribute:
                _LOGGER.warning(
                    "%s attribute %s is not numerical",
                    self._source_entity_id,
                    self._source_attribute,
                )
            else:
                _LOGGER.warning("%s state is not numerical", self._source_entity_id)

        self.async_write_ha_state()
