"""Support for IoTaWatt Energy monitor."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging

from iotawattpy.sensor import Sensor

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    CONF_HOST,
    PERCENTAGE,
    UnitOfApparentPower,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfReactiveEnergy,
    UnitOfReactivePower,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import CONF_INTEGRATE_REACTIVE, DOMAIN, VOLT_AMPERE_REACTIVE_HOURS
from .coordinator import IotawattConfigEntry, IotawattUpdater

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class IotaWattSensorEntityDescription(SensorEntityDescription):
    """Class describing IotaWatt sensor entities."""

    value: Callable | None = None


ENTITY_DESCRIPTION_KEY_MAP: dict[str, IotaWattSensorEntityDescription] = {
    "Amps": IotaWattSensorEntityDescription(
        key="Amps",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.CURRENT,
        entity_registry_enabled_default=False,
    ),
    "Hz": IotaWattSensorEntityDescription(
        key="Hz",
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.FREQUENCY,
        icon="mdi:flash",
        entity_registry_enabled_default=False,
    ),
    "PF": IotaWattSensorEntityDescription(
        key="PF",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER_FACTOR,
        value=lambda value: value * 100,
        entity_registry_enabled_default=False,
    ),
    "Watts": IotaWattSensorEntityDescription(
        key="Watts",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
    ),
    "WattHours": IotaWattSensorEntityDescription(
        key="WattHours",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.ENERGY,
    ),
    "VA": IotaWattSensorEntityDescription(
        key="VA",
        native_unit_of_measurement=UnitOfApparentPower.VOLT_AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.APPARENT_POWER,
        entity_registry_enabled_default=False,
    ),
    "VAR": IotaWattSensorEntityDescription(
        key="VAR",
        native_unit_of_measurement=UnitOfReactivePower.VOLT_AMPERE_REACTIVE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.REACTIVE_POWER,
        entity_registry_enabled_default=False,
    ),
    "VARh": IotaWattSensorEntityDescription(
        key="VARh",
        native_unit_of_measurement=VOLT_AMPERE_REACTIVE_HOURS,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:flash",
        entity_registry_enabled_default=False,
    ),
    "Volts": IotaWattSensorEntityDescription(
        key="Volts",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.VOLTAGE,
        entity_registry_enabled_default=False,
    ),
}


# Energy integrated since the start of the IoTaWatt datalog. It never resets,
# so it suits the Energy dashboard and total_increasing statistics.
LIFETIME_ENERGY_DESCRIPTION = IotaWattSensorEntityDescription(
    key="WattHoursLifetime",
    native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
    suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
    state_class=SensorStateClass.TOTAL_INCREASING,
    device_class=SensorDeviceClass.ENERGY,
)

# Reactive energy integrated since the start of the IoTaWatt datalog. Reactive
# energy can be negative (capacitive loads), so it is a total, not increasing.
REACTIVE_ENERGY_TOTAL_DESCRIPTION = IotaWattSensorEntityDescription(
    key="VARhTotal",
    native_unit_of_measurement=UnitOfReactiveEnergy.VOLT_AMPERE_REACTIVE_HOUR,
    state_class=SensorStateClass.TOTAL,
    device_class=SensorDeviceClass.REACTIVE_ENERGY,
    entity_registry_enabled_default=False,
)


def _get_description(
    entry: IotawattConfigEntry, data: Sensor
) -> IotaWattSensorEntityDescription:
    """Return the entity description for a sensor."""
    unit = data.getUnit()
    if unit == "WattHours" and data.getLifetime():
        return LIFETIME_ENERGY_DESCRIPTION
    if unit == "VARh" and entry.options.get(CONF_INTEGRATE_REACTIVE, False):
        return REACTIVE_ENERGY_TOTAL_DESCRIPTION
    return ENTITY_DESCRIPTION_KEY_MAP.get(
        unit, IotaWattSensorEntityDescription(key="base_sensor")
    )


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: IotawattConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add sensors for passed config_entry in HA."""
    coordinator = config_entry.runtime_data
    created = set()

    @callback
    def _create_entity(key: str) -> IotaWattSensor:
        """Create a sensor entity."""
        created.add(key)
        data = coordinator.data["sensors"][key]
        description = _get_description(config_entry, data)

        return IotaWattSensor(
            coordinator=coordinator,
            key=key,
            entity_description=description,
        )

    async_add_entities(_create_entity(key) for key in coordinator.data["sensors"])

    @callback
    def new_data_received():
        """Check for new sensors."""
        entities = [
            _create_entity(key)
            for key in coordinator.data["sensors"]
            if key not in created
        ]
        async_add_entities(entities)

    config_entry.async_on_unload(coordinator.async_add_listener(new_data_received))


class IotaWattSensor(CoordinatorEntity[IotawattUpdater], SensorEntity):
    """Defines a IoTaWatt Energy Sensor."""

    entity_description: IotaWattSensorEntityDescription

    def __init__(
        self,
        coordinator: IotawattUpdater,
        key: str,
        entity_description: IotaWattSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator=coordinator)

        self._key = key
        data = self._sensor_data
        if data.getType() == "Input":
            self._attr_unique_id = (
                f"{data.hub_mac_address}-input-{data.getChannel()}-{data.getUnit()}"
            )
        elif data.getType() == "Output":
            self._attr_unique_id = f"{data.hub_mac_address}-output-{data.getSourceName()}"
        if self._attr_unique_id and data.getLifetime():
            # Lifetime sensors share the source name and unit of the daily
            # energy sensors, so they need their own suffix.
            self._attr_unique_id += "-lifetime"
        self._attr_name = data.getName()
        self.entity_description = entity_description
        self._update_last_reset()

    @property
    def _sensor_data(self) -> Sensor:
        """Return sensor data."""
        return self.coordinator.data["sensors"][self._key]

    @property
    def device_info(self) -> dr.DeviceInfo:
        """Return device info."""
        mac = self._sensor_data.hub_mac_address
        return dr.DeviceInfo(
            identifiers={(DOMAIN, mac)},
            connections={(dr.CONNECTION_NETWORK_MAC, mac)},
            manufacturer="IoTaWatt",
            model="IoTaWatt",
            # No device name: HA 2026.10+ prefixes every friendly name with it.
            name=None,
            configuration_url=f"http://{self.coordinator.config_entry.data[CONF_HOST]}",
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if self._key not in self.coordinator.data["sensors"]:
            # Keep the entity and its registry entry; it is shown as unavailable
            # until the sensor is reported by the IoTaWatt again.
            self.async_write_ha_state()
            return

        self._attr_name = self._sensor_data.getName()
        self._update_last_reset()
        super()._handle_coordinator_update()

    def _update_last_reset(self) -> None:
        """Set last_reset from the start of the IoTaWatt integration period."""
        # Only the daily energy sensors reset; lifetime totals have no last_reset.
        if (
            self.entity_description.key == "WattHours"
            and (begin := self._sensor_data.getBegin())
            and (last_reset := dt_util.parse_datetime(begin))
        ):
            self._attr_last_reset = last_reset

    @property
    def available(self) -> bool:
        """Return if the sensor is still reported by the IoTaWatt."""
        return super().available and self._key in self.coordinator.data["sensors"]

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Return the extra state attributes of the entity."""
        data = self._sensor_data
        attrs = {"type": data.getType()}
        if attrs["type"] == "Input":
            attrs["channel"] = data.getChannel()

        return attrs

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        if func := self.entity_description.value:
            return func(self._sensor_data.getValue())

        return self._sensor_data.getValue()
