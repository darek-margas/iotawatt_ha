"""IoTaWatt DataUpdateCoordinator."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from iotawattpy.iotawatt import Iotawatt

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import httpx_client
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONNECTION_ERRORS

_LOGGER = logging.getLogger(__name__)

# Matches iotwatt data log interval
REQUEST_REFRESH_DEFAULT_COOLDOWN = 5

type IotawattConfigEntry = ConfigEntry[IotawattUpdater]


class IotawattUpdater(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching update data from the IoTaWatt Energy Device."""

    config_entry: IotawattConfigEntry
    api: Iotawatt | None = None

    def __init__(self, hass: HomeAssistant, entry: IotawattConfigEntry) -> None:
        """Initialize IotaWattUpdater object."""
        super().__init__(
            hass=hass,
            logger=_LOGGER,
            config_entry=entry,
            name=entry.title,
            update_interval=timedelta(seconds=30),
            request_refresh_debouncer=Debouncer(
                hass,
                _LOGGER,
                cooldown=REQUEST_REFRESH_DEFAULT_COOLDOWN,
                immediate=True,
            ),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch sensors from IoTaWatt device."""
        if self.api is None:
            entry = self.config_entry
            api = Iotawatt(
                entry.title,
                entry.data[CONF_HOST],
                httpx_client.get_async_client(self.hass),
                entry.data.get(CONF_USERNAME),
                entry.data.get(CONF_PASSWORD),
                integratedInterval="d",
                includeNonTotalSensors=False,
            )
            try:
                is_authenticated = await api.connect()
            except CONNECTION_ERRORS as err:
                raise UpdateFailed("Connection failed") from err

            if not is_authenticated:
                raise ConfigEntryAuthFailed("Authentication error")

            self.api = api

        try:
            await self.api.update()
        except CONNECTION_ERRORS as err:
            # Reconnect on the next refresh, so a changed password is detected
            # and reported as an authentication failure.
            self.api = None
            raise UpdateFailed(f"Error communicating with IoTaWatt: {err}") from err
        return self.api.getSensors()
