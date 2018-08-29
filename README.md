# Meross IoT library
A pure-python based library providing API for controlling Meross IoT devices over the internet.
At the moment there is only support for the **Meross Mss310** smart plug.
Hopefully, more Meross hardware will be supported in the future.

This library is still work in progress, therefore use it with caution.

## Usage
The following script demonstrates how to use this library.

```python
import time
import sys
from meross_cloud import MerossHttpClient

if __name__=='__main__':
    httpHandler = MerossHttpClient(email="YOUR_MEROSS_CLOUD_EMAIL", password="YOUR_PASSWORD")

    # Retrieves the list of supported devices
    devices = httpHandler.list_supported_devices()

    # Returns most of the info about the power plug
    data = devices[0].get_sys_data()

    # Turns the power-plug on
    devices[0].turn_off()

    # Turns the power-plug off
    devices[0].turn_on()

    # Reads the historical device consumption
    consumption = devices[0].get_power_consumptionX()

    # Returns the list of WIFI Network available for the plug
    # (Note. this takes some time to complete)
    wifi_list = devices[0].get_wifi_list()

    # Info about the device
    trace = devices[0].get_trace()
    debug = devices[0].get_debug()

    # Returns the capabilities of this device
    abilities = devices[0].get_abilities()

    # I still have to figure this out :S
    report = devices[0].get_report()

    # Returns the current power consumption and voltage from the plug
    # (Note: this is not really realtime, but close enough)
    electricity = devices[0].get_electricity()

    current_status = devices[0].get_electricity()
    print(current_status)

```

## Meross protocol details
This library was implemented by reverse-engineering the network communications between the plug and the meross network.
Anyone can do the same by simply installing a Man-In-The-Middle proxy and routing the ssl traffic of an Android emulator through the sniffer.

The following section is a work in progress and I'll update it as soon as possible.

### HTTP methods
#### Login
#### List devices
#### Logout

### MQTT communications
#### Connect to MQTT server
client-id

#### Topics

#### Command format

#### Some command examples

