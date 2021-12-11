---
title: Calibration
description: Instructions on how to integrate calibration sensors into Home Assistant.
ha_category:
  - Utility
  - Sensor
ha_iot_class: Calculated
ha_release: '2021.5'
ha_codeowners:
  - '@lymanepp'
ha_domain: calibration
ha_platforms:
  - sensor
---

The Calibration integration consumes the state from other sensors. It exports the calibrated value as state and the following values as attributes: `entity_id` and `coefficients`.  A single polynomial, linear by default, is fit to all data points provided.

## Configuration

To enable the calibration sensor, add the following lines to your `configuration.yaml`:

```yaml
# Example configuration.yaml entry
calibration:
  media_player_db_volume:
    source: media_player.yamaha_receiver
    attribute: volume_level
    unit_of_measurement: dB
    data_points:
      - [0.2, -80.0]
      - [1.0, 0.0]
```

{% configuration %}
source:
  description: The entity to monitor.
  required: true
  type: string
data_points:
  description: "The collection of data point conversions with the format `[uncalibrated_value, calibrated_value]`.  e.g., `[1.0, 2.1]`. The number of required data points is equal to the polynomial `degree` + 1. For example, a linear calibration (with `degree: 1`) requires at least 2 data points."
  required: true
  type: list
unique_id:
  description: An ID that uniquely identifies this sensor. Set this to a unique value to allow customization through the UI.
  required: false
  type: string
attribute:
  description: Attribute to monitor.
  required: false
  type: string
friendly_name:
  description: Set the friendly name for the new sensor.
  required: false
  type: string
device_class:
  description: Set the device class for the new sensor. By default, the device class from the monitored entity will be used (except for attributes).
  required: false
  type: string
degree:
  description: "The degree of a polynomial. e.g., Linear calibration (y = x + 3) has 1 degree, Quadratic calibration (y = x<sup>2</sup> + x + 3) has 2 degrees, etc."
  required: false
  default: 1
  type: integer
precision:
  description: Defines the precision of the calculated values, through the argument of round().
  required: false
  default: 2
  type: integer
unit_of_measurement:
  description: Defines the units of measurement of the sensor, if any. By default, the units of measurement from the monitored entity will be used (except for attributes).
  required: false
  type: string
{% endconfiguration %}
