import os
from meross_iot.api import MerossHttpClient
from meross_iot.supported_devices.power_plugs import GenericPlug
from meross_iot.supported_devices.light_bulbs import GenericBulb


EMAIL = os.environ.get('MEROSS_EMAIL') or 'YOUR_MEROSS_CLOUD_EMAIL'
PASSWORD = os.environ.get('MEROSS_PASSWORD') or 'YOUR_MEROSS_CLOUD_EMAIL'


if __name__=='__main__':
    httpHandler = MerossHttpClient(email=EMAIL, password=PASSWORD)

    print("Listing online devices...")

    # Retrieves the list of supported and ONLINE devices.
    # If you also want to list offline devices, pass the online_only=False parameter.
    # Note! Trying to control an offline device will generate an exception.
    devices = httpHandler.list_supported_devices()
    for d in devices:
        print("-", d)

    for device in devices:
        print("\n-------------------------------\n"
              "Playing with device: %s"
              "\n-------------------------------" % device)

        # Returns most of the info about the power plug
        print("\nGetting system data...")
        data = device.get_sys_data()
        print(data)

        # If the device supports multiple channels, let's play with each one.
        n_channels = len(device.get_channels())
        print("The device supports %d channels" % n_channels)

        for channel in range(0, n_channels):
            # Turns the power-plug on
            print("\nTurning channel %d on..." % channel)
            device.turn_on_channel(channel)

            # Turns the power-plug off
            print("Turning channel %d off..." % channel)
            device.turn_off_channel(channel)

        # If the current device is a bulb, let's play with it!
        if isinstance(device, GenericBulb) and device.supports_light_control():
            print("Controlling light color: make it blue at 50% power")
            device.set_light_color(rgb=(0, 0, 255), luminance=50)
            device.turn_on()

        # Some devices also have a dedicated channel for USB
        if isinstance(device, GenericPlug):
            usb_channel_index = device.get_usb_channel_index()
            if usb_channel_index is not None:
                # Turns the USB on
                print("\nTurning on USB...")
                device.turn_on_channel(usb_channel_index)

                # Turns the power-plug off
                print("Turning off USB...")
                device.turn_off_channel(usb_channel_index)

            # Some devices support reading consumption data
            if device.supports_consumption_reading():
                print("\nReading consumption data...")
                consumption = device.get_power_consumption()
                print(consumption)

            # Some devices support reading consumption data
            if device.supports_electricity_reading():
                print("\nReading electricity data...")
                electricity = device.get_electricity()
                print(electricity)

        # Returns the list of WIFI Network available for the plug
        # (Note. this takes some time to complete)
        print("\nScanning Wifi...")
        wifi_list = device.get_wifi_list()
        print(wifi_list)
