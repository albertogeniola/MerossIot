# Meross IoT library
A pure-python based library providing API for controlling Meross IoT devices over the internet.

To see what devices are currently supported, checkout the `Currently supported devices`-section. 
Hopefully, more Meross hardware will be supported in the future.

This library is still work in progress, therefore use it with caution.

## Installation
Due to the popularity of the library, I've decided to list it publicly on the Pipy index.
So, the installation is as simple as typing the following command:

```
pip install meross_iot --upgrade
```

## Usage
The following script demonstrates how to use this library.

```python
import time
import sys
from meross_iot.api import MerossHttpClient

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

## Currently supported devices
Even though this library was firstly meant to drive only the Meross MSS310, 
other nice developers contributed to its realization. The following is the 
currently supported list of devices:

- MSS310
- MSS110 (Thanks to [soberstadt](https://github.com/soberstadt))
- MSS425E (Thanks to [ping-localhost](https://github.com/ping-localhost))

## Protocol details
This library was implemented by reverse-engineering the network communications between the plug and the meross network.
Anyone can do the same by simply installing a Man-In-The-Middle proxy and routing the ssl traffic of an Android emulator through the sniffer.

If you want to understand how the Meross protocol works, [have a look at the Wiki](https://github.com/albertogeniola/MerossIot/wiki). Be aware: this is still work in progress, so some pages of the wiki might still be blank/under construction.

## Donate!
I like reverse engineering and protocol inspection, I think it keeps your mind trained and healthy. However, if you liked or appreciated by work, why don't you buy me a beer? It would really motivate me to continue working on this repository to improve documentation, code and extend the supported meross devices.

[![Buy me a beer](http://4.bp.blogspot.com/-1Md6-deTZ84/VA_lzcxMx1I/AAAAAAAACl8/wP_4rXBXwyI/s1600/PayPal-Donation-Button.png)](https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=6HPAB89UYSZF2)



