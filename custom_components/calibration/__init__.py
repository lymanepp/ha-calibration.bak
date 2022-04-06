"""The Calibration integration."""
import logging

import numpy as np
import voluptuous as vol
from homeassistant.components.sensor import DEVICE_CLASSES_SCHEMA
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.const import (
    CONF_ATTRIBUTE,
    CONF_DEVICE_CLASS,
    CONF_FRIENDLY_NAME,
    CONF_SOURCE,
    CONF_UNIQUE_ID,
    CONF_UNIT_OF_MEASUREMENT,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_CALIBRATION,
    CONF_DATAPOINTS,
    CONF_DEGREE,
    CONF_POLYNOMIAL,
    CONF_PRECISION,
    DATA_CALIBRATION,
    DEFAULT_DEGREE,
    DEFAULT_PRECISION,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


def datapoints_greater_than_degree(value: dict) -> dict:
    """Validate data point list is greater than polynomial degrees."""
    if len(value[CONF_DATAPOINTS]) <= value[CONF_DEGREE]:
        raise vol.Invalid(
            f"{CONF_DATAPOINTS} must have at least {value[CONF_DEGREE]+1} {CONF_DATAPOINTS}"
        )

    return value


CALIBRATION_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SOURCE): cv.entity_id,
        vol.Required(CONF_DATAPOINTS): [
            vol.ExactSequence([vol.Coerce(float), vol.Coerce(float)])
        ],
        vol.Optional(CONF_UNIQUE_ID): cv.string,
        vol.Optional(CONF_ATTRIBUTE): cv.string,
        vol.Optional(CONF_PRECISION, default=DEFAULT_PRECISION): cv.positive_int,
        vol.Optional(CONF_DEGREE, default=DEFAULT_DEGREE): vol.All(
            vol.Coerce(int),
            vol.Range(min=1, max=7),
        ),
        vol.Optional(CONF_FRIENDLY_NAME): cv.string,
        vol.Optional(CONF_DEVICE_CLASS): DEVICE_CLASSES_SCHEMA,
        vol.Optional(CONF_UNIT_OF_MEASUREMENT): cv.string,
    }
)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {cv.slug: vol.All(CALIBRATION_SCHEMA, datapoints_greater_than_degree)}
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: ConfigType):
    """Set up the Calibration sensor."""
    hass.data[DATA_CALIBRATION] = {}

    for calibration, conf in config.get(DOMAIN, {}).items():
        _LOGGER.debug("Setup %s.%s", DOMAIN, calibration)

        degree = conf[CONF_DEGREE]

        # get x values and y values from the x,y point pairs
        x_values, y_values = zip(*conf[CONF_DATAPOINTS])

        # try to get valid coefficients for a polynomial
        coefficients = None
        with np.errstate(all="raise"):
            try:
                coefficients = np.polyfit(x_values, y_values, degree)
            except FloatingPointError as error:
                _LOGGER.error(
                    "Setup of %s encountered an error, %s",
                    calibration,
                    error,
                )

        if coefficients is not None:
            data = {
                k: v for k, v in conf.items() if k not in [CONF_DEGREE, CONF_DATAPOINTS]
            }
            data[CONF_POLYNOMIAL] = np.poly1d(coefficients)

            hass.data[DATA_CALIBRATION][calibration] = data

            hass.async_create_task(
                async_load_platform(
                    hass,
                    SENSOR_DOMAIN,
                    DOMAIN,
                    {CONF_CALIBRATION: calibration},
                    config,
                )
            )

    return True
