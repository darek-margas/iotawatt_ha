"""Constants for the IoTaWatt integration."""

from __future__ import annotations

import json

import httpx

DOMAIN = "iotawatt"
VOLT_AMPERE_REACTIVE = "VAR"
VOLT_AMPERE_REACTIVE_HOURS = "VARh"

CONF_LIFETIME_SENSORS = "lifetime_sensors"
CONF_INTEGRATE_REACTIVE = "integrate_reactive"

CONNECTION_ERRORS = (KeyError, json.JSONDecodeError, httpx.HTTPError)
