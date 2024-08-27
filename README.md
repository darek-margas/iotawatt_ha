# Home Assistant Integration for IoTaWatt, Open WiFi Electricity Monitor

This project provides [IoTaWatt](https://iotawatt.com/) support through a
custom integration for Home Assistant. It creates entites for each input and
output present in IoTaWatt.

This integration was incorporated into the 2021.9 core, but it faced criticism from the core team due to the generated unique IDs not being sufficiently unique. As a result, the functionality of output unique IDs was removed from the core version, which led to a less efficient setup with output sensors scattered across different places.

The original custom integration kept this feature, but it became dormant and gradually diverged from the updated core version.

I have updated this repository by backporting the core version while retaining the unique IDs.

The integration isn't available in HACS by default, but it can be installed as a custom repository via HACS or downloaded manually.
