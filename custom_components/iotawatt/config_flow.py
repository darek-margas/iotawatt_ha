"""Config flow for iotawatt integration."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

from iotawattpy.iotawatt import Iotawatt
import voluptuous as vol

from homeassistant.config_entries import (
    SOURCE_RECONFIGURE,
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import httpx_client
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    CONF_INTEGRATE_REACTIVE,
    CONF_LIFETIME_SENSORS,
    CONNECTION_ERRORS,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

PASSWORD_SELECTOR = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))


def _auth_schema(username: str = "") -> vol.Schema:
    """Return the schema for the username and password form."""
    return vol.Schema(
        {
            vol.Required(CONF_USERNAME, default=username): str,
            vol.Required(CONF_PASSWORD): PASSWORD_SELECTOR,
        }
    )


async def validate_input(hass: HomeAssistant, data: Mapping[str, Any]) -> dict[str, str]:
    """Validate the user input allows us to connect."""
    iotawatt = Iotawatt(
        "",
        data[CONF_HOST],
        httpx_client.get_async_client(hass),
        data.get(CONF_USERNAME),
        data.get(CONF_PASSWORD),
    )
    try:
        is_connected = await iotawatt.connect()
    except CONNECTION_ERRORS:
        return {"base": "cannot_connect"}
    except Exception:
        _LOGGER.exception("Unexpected exception")
        return {"base": "unknown"}

    if not is_connected:
        return {"base": "invalid_auth"}

    return {}


class IOTaWattConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for iotawatt."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize."""
        self._data: dict[str, Any] = {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> IotawattOptionsFlow:
        """Return the options flow."""
        return IotawattOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        if user_input is None:
            user_input = {}

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=user_input.get(CONF_HOST, "")): str,
            }
        )
        if not user_input:
            return self.async_show_form(step_id="user", data_schema=schema)

        self._async_abort_entries_match({CONF_HOST: user_input[CONF_HOST]})

        if not (errors := await validate_input(self.hass, user_input)):
            return self.async_create_entry(title=user_input[CONF_HOST], data=user_input)

        if errors == {"base": "invalid_auth"}:
            self._data.update(user_input)
            return await self.async_step_auth()

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_auth(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Authenticate user if authentication is enabled on the IoTaWatt device."""
        if not user_input:
            return self.async_show_form(step_id="auth", data_schema=_auth_schema())

        data = {**self._data, **user_input}

        if errors := await validate_input(self.hass, data):
            return self.async_show_form(
                step_id="auth",
                data_schema=_auth_schema(user_input[CONF_USERNAME]),
                errors=errors,
            )

        if self.source == SOURCE_RECONFIGURE:
            return self._async_update_reconfigured_entry(data)

        return self.async_create_entry(title=data[CONF_HOST], data=data)

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle a failed authentication on an existing entry."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for new credentials."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            data = {**entry.data, **user_input}
            if not (errors := await validate_input(self.hass, data)):
                return self.async_update_reload_and_abort(entry, data_updates=user_input)

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=_auth_schema(
                (user_input or entry.data).get(CONF_USERNAME) or ""
            ),
            description_placeholders={CONF_HOST: entry.data[CONF_HOST]},
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change the host of an existing entry."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            # Keep existing credentials; the device may not need them any more,
            # in which case they are ignored.
            data = {**entry.data, **user_input}
            if not (errors := await validate_input(self.hass, data)):
                return self._async_update_reconfigured_entry(data)

            if errors == {"base": "invalid_auth"}:
                self._data = {CONF_HOST: user_input[CONF_HOST]}
                return await self.async_step_auth()

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_HOST,
                        default=(user_input or entry.data)[CONF_HOST],
                    ): str,
                }
            ),
            errors=errors,
        )

    def _async_update_reconfigured_entry(self, data: dict[str, Any]) -> ConfigFlowResult:
        """Save a reconfigured entry, renaming it if it is still named after its host."""
        entry = self._get_reconfigure_entry()
        title = entry.title
        if title == entry.data[CONF_HOST]:
            title = data[CONF_HOST]
        return self.async_update_reload_and_abort(entry, title=title, data=data)


class IotawattOptionsFlow(OptionsFlow):
    """Handle IoTaWatt options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Choose which optional sensors to create."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        options = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_LIFETIME_SENSORS,
                        default=options.get(CONF_LIFETIME_SENSORS, False),
                    ): bool,
                    vol.Required(
                        CONF_INTEGRATE_REACTIVE,
                        default=options.get(CONF_INTEGRATE_REACTIVE, False),
                    ): bool,
                }
            ),
        )
