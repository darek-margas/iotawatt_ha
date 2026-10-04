# Home Assistant Integration for IoTaWatt, Open WiFi Electricity Monitor

This project provides [IoTaWatt](https://iotawatt.com/) support through a
custom integration for Home Assistant. It creates entities for each input and
output present in IoTaWatt.

## What is IoTaWatt?

IoTaWatt is an open-source, Wi-Fi connected electricity monitor that sits in
or next to your switchboard (breaker panel). It measures up to 14 circuits
using clip-on current transformers (CTs) and a voltage reference, and records
power, energy, voltage, current, power factor and frequency locally on the
device, with no cloud service required.

In IoTaWatt you configure:

- **Inputs**: the physical channels, one per CT or voltage reference, for
  example "Hot water", "Air conditioner" or "Mains phase A".
- **Outputs**: calculated values built from inputs, for example
  "Total consumption = Mains A + Mains B", "House minus solar" or
  "Everything not individually measured".

## What does this integration do?

It reads data from the IoTaWatt over your local network and creates Home
Assistant sensors for every input and output, so you can:

- use them in the **Energy dashboard** (each power input also gets a daily
  energy sensor in Wh),
- show live power use on dashboards,
- trigger automations, for example "notify me when the dryer finishes" or
  "turn the pool pump off when the house draws more than X kW",
- keep long-term statistics and history.

Power (W) and daily energy (Wh) sensors are enabled by default. Voltage,
current, frequency, power factor, apparent power (VA) and reactive power (VAR,
VARh) sensors are created but disabled; enable the ones you need in
**Settings → Devices & services → Entities**.

## Why this custom integration instead of the built-in one?

An IoTaWatt integration has been part of Home Assistant core since 2021.9, but
it doesn't give **outputs** a unique ID.

A unique ID is what lets Home Assistant remember an entity between restarts.
Without one, an entity can't be managed from the UI: you can't rename it,
change its entity ID or icon, assign it to an area, or tidy it up, and it's
harder to keep it stable in the Energy dashboard and long-term statistics.
Since outputs are usually the most useful IoTaWatt values (totals, net
consumption, "rest of house"), this matters.

The core team removed the output unique IDs because they're built from the
output's name, which they didn't consider unique or stable enough. As a
result, output sensors in the core version can't be customised and end up
scattered rather than grouped and managed alongside the inputs.

The original custom integration kept this feature, but it became dormant and
gradually diverged from the updated core version. This repository backports
the core version and keeps the unique IDs for outputs, and also includes a
few bug fixes of its own (see the releases).

**Note:** because an output's unique ID is based on its name, renaming an
output in the IoTaWatt creates a new entity in Home Assistant. The old entity
becomes unavailable and can be deleted from **Settings → Entities**.

## IoTaWatt hardware availability

Manufacturing of the IoTaWatt has stopped, so new units are no longer
available from the original maker. The project is open source: the firmware
source code is available at
[github.com/boblemaire/IoTaWatt](https://github.com/boblemaire/IoTaWatt), so
existing devices keep working and hobbyists can continue to build, maintain
and develop it. This integration remains available for everyone with an
IoTaWatt.

## Installation

The integration isn't in the default HACS list, but it can be installed as a
custom repository via HACS or copied manually.

**HACS**

1. In HACS, open the menu (⋮) → **Custom repositories**.
2. Add `https://github.com/darek-margas/iotawatt_ha` with category
   **Integration**.
3. Install **IoTaWatt** and restart Home Assistant.

**Manual**

1. Copy `custom_components/iotawatt` into your Home Assistant
   `config/custom_components/` folder.
2. Restart Home Assistant.

Because it uses the same domain (`iotawatt`), this custom integration replaces
the built-in one. Home Assistant will log a warning that a custom integration
overrides a core one; that's expected.

## Configuration

Go to **Settings → Devices & services → Add integration → IoTaWatt** and
enter the IoTaWatt's host name or IP address. If authentication is enabled on
the device, you'll be asked for the username and password.

- If the IoTaWatt's address changes, use **Reconfigure** on the integration
  entry instead of removing and re-adding it.
- If the IoTaWatt's password changes, Home Assistant shows a notification
  asking you to re-enter the credentials.

Requires Home Assistant 2025.2 or newer.

## Polling

By default the integration polls the IoTaWatt every 30 seconds. The IoTaWatt
logs data every 5 seconds, and the integration won't fetch more often than
once every 5 seconds.

If you want faster updates, disable automatic polling (integration entry → ⋮ →
**System options** → turn off **Enable polling for changes**) and call the
`homeassistant.update_entity` action on a schedule, for example every
5 seconds, targeting a single IoTaWatt entity. One entity is enough because
all sensors are refreshed together.
