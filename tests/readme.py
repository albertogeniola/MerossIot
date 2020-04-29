import os
import time
from random import randint

from meross_iot.cloud.devices.door_openers import GenericGarageDoorOpener
from meross_iot.cloud.devices.hubs import GenericHub
from meross_iot.cloud.devices.humidifier import GenericHumidifier, SprayMode
from meross_iot.cloud.devices.light_bulbs import GenericBulb
from meross_iot.cloud.devices.power_plugs import GenericPlug
from meross_iot.cloud.devices.subdevices.sensors import SensorSubDevice
from meross_iot.cloud.devices.subdevices.thermostats import ValveSubDevice, ThermostatV3Mode
from meross_iot.manager import MerossManager
from meross_iot.model.events import MerossEventType

EMAIL = os.environ.get('MEROSS_EMAIL') or "YOUR_MEROSS_CLOUD_EMAIL"
PASSWORD = os.environ.get('MEROSS_PASSWORD') or "YOUR_MEROSS_CLOUD_PASSWORD"


def event_handler(eventobj):
    if eventobj.event_type == MerossEventType.DEVICE_ONLINE_STATUS:
        print("Device online status changed: %s went %s" % (eventobj.device.name, eventobj.status))
        pass

    elif eventobj.event_type == MerossEventType.DEVICE_SWITCH_STATUS:
        print("Switch state changed: Device %s (channel %d) went %s" % (eventobj.device.name, eventobj.channel_id,
                                                                        eventobj.switch_state))
    elif eventobj.event_type == MerossEventType.CLIENT_CONNECTION:
        print("MQTT connection state changed: client went %s" % eventobj.status)

        # TODO: Give example of reconnection?

    elif eventobj.event_type == MerossEventType.GARAGE_DOOR_STATUS:
        print("Garage door is now %s" % eventobj.door_state)

    elif eventobj.event_type == MerossEventType.THERMOSTAT_MODE_CHANGE:
        print("Thermostat %s has changed mode to %s" % (eventobj.device.name, eventobj.mode))

    elif eventobj.event_type == MerossEventType.THERMOSTAT_TEMPERATURE_CHANGE:
        print("Thermostat %s has revealed a temperature change: %s" % (eventobj.device.name, eventobj.temperature))

    elif eventobj.event_type == MerossEventType.SENSOR_TEMPERATURE_CHANGE:
        print("Sensor %s has revealed a temp/humidity change: %s / %s" % (eventobj.device.name, eventobj.temperature, eventobj.humidity))

    elif eventobj.event_type == MerossEventType.SENSOR_TEMPERATURE_ALERT:
        print("Sensor %s has revealed a temp/humidity alert: %s" % (eventobj.device.name, eventobj.alert))

    else:
        print("Unknown event!")


if __name__ == '__main__':
    # Initiates the Meross Cloud Manager. This is in charge of handling the communication with the remote endpoint
    manager = MerossManager.from_email_and_password(meross_email=EMAIL, meross_password=PASSWORD)

    # Register event handlers for the manager...
    manager.register_event_handler(event_handler)

    # Starts the manager
    manager.start()

    # You can retrieve the device you are looking for in various ways:
    # By kind
    bulbs = manager.get_devices_by_kind(GenericBulb)
    plugs = manager.get_devices_by_kind(GenericPlug)
    door_openers = manager.get_devices_by_kind(GenericGarageDoorOpener)
    hub_devices = manager.get_devices_by_kind(GenericHub)
    thermostats = manager.get_devices_by_kind(ValveSubDevice)
    sensors = manager.get_devices_by_kind(SensorSubDevice)
    humidifiers = manager.get_devices_by_kind(GenericHumidifier)
    all_devices = manager.get_supported_devices()

    # Print some basic specs about the discovered devices
    print("All the bulbs I found:")
    for b in bulbs:
        print(b)

    print("All the plugs I found:")
    for p in plugs:
        print(p)

    print("All the garage openers I found:")
    for g in door_openers:
        print(g)

    print("All the humidifier I found:")
    for h in all_devices:
        print(h)

    print("All the hubs I found:")
    for h in hub_devices:
        print(h)

    print("All the hub devices I found:")
    for d in all_devices:
        print(d)

    # You can also retrieve devices by the UUID/name
    # a_device = manager.get_device_by_name("My Plug")
    # a_device = manager.get_device_by_uuid("My Plug")
    # Or you can retrieve all the device by the HW type
    # all_mss310 = manager.get_devices_by_type("mss310")
    # ------------------------------
    # Let's play the garage openers.
    # ------------------------------
    for g in door_openers:
        if not g.online:
            print("The garage controller %s seems to be offline. Cannot play with that..." % g.name)
            continue
        print("Opening door %s..." % g.name)
        g.open_door()
        print("Closing door %s..." % g.name)
        g.close_door()

    # ---------------------
    # Let's play with bulbs
    # ---------------------
    for b in bulbs:  # type: GenericBulb
        if not b.online:
            print("The bulb %s seems to be offline. Cannot play with that..." % b.name)
            continue
        print("Let's play with bulb %s" % b.name)
        if not b.supports_light_control():
            print("Too bad bulb %s does not support light control %s" % b.name)
        else:
            # Is this an rgb bulb?
            if b.is_rgb():
                # Let's make it red!
                b.set_light_color(rgb=(255, 0, 0))

            time.sleep(1)

            if b.is_light_temperature():
                b.set_light_color(temperature=10)

            time.sleep(1)

            # Let's dimm its brightness
            if b.supports_luminance():
                random_luminance = randint(10, 100)
                b.set_light_color(luminance=random_luminance)

        b.turn_on()
        time.sleep(1)
        b.turn_off()

    # ---------------------------
    # Let's play with smart plugs
    # ---------------------------
    for p in plugs:  # type: GenericPlug
        if not p.online:
            print("The plug %s seems to be offline. Cannot play with that..." % p.name)
            continue

        print("Let's play with smart plug %s" % p.name)

        channels = len(p.get_channels())
        print("The plug %s supports %d channels." % (p.name, channels))
        for i in range(0, channels):
            print("Turning on channel %d of %s" % (i, p.name))
            p.turn_on_channel(i)

            time.sleep(1)

            print("Turning off channel %d of %s" % (i, p.name))
            p.turn_off_channel(i)

        usb_channel = p.get_usb_channel_index()
        if usb_channel is not None:
            print("Awesome! This device also supports USB power.")
            p.enable_usb()
            time.sleep(1)
            p.disable_usb()

        if p.supports_electricity_reading():
            print("Awesome! This device also supports power consumption reading.")
            print("Current consumption is: %s" % str(p.get_electricity()))

    # ---------------------
    # Let's play with smart humidifier
    # ---------------------
    for h in humidifiers:  # type: GenericHumidifier
        if not h.online:
            print("Smart humidifier %s seems to be offline. Cannot play with it at this time..." % h.name)
            continue

        # Let's set its color to RED
        print("Setting the smart humidifier %s color to red" % h.name)
        h.configure_light(onoff=1, rgb=(255, 0, 0), luminance=100)
        print("Setting spray-mode to CONTINUOUS")
        h.set_spray_mode(spray_mode=SprayMode.CONTINUOUS)
        print("Waiting a bit before turning it off...")
        time.sleep(10)
        print("Setting spray-mode to OFF")
        h.set_spray_mode(spray_mode=SprayMode.OFF)

    # ---------------------------
    # Let's play with the Thermostat
    # ---------------------------
    for t in thermostats:  # type: ValveSubDevice
        if not t.online:
            print("The thermostat %s seems to be offline. Cannot play with that..." % t.name)
            continue

        # Get the current preset mode
        print("Current mode: %s" % t.mode)
        print("Let's change the preset mode")
        t.set_mode(ThermostatV3Mode.COOL)

        # Note that the thermostat will not receive the command instantly, as it needs to be sent by the HUB via its
        # low power communication channel. So, we need to wait a bit until it gets received.
        print("Waiting a minute...")
        time.sleep(60)
        print("Current mode: %s" % t.mode)

        # Set the target temperature
        target_temp = randint(10,30)
        print("Setting the target temperature to %f" % target_temp)
        t.set_target_temperature(target_temp=target_temp)

        # Note that the thermostat will not receive the command instantly, as it needs to be sent by the HUB via its
        # low power communication channel. So, we need to wait a bit until it gets received.
        time.sleep(60)
        print("Current mode: %s" % t.mode)

    # ---------------------------
    # Let's check on the Sensors
    # ---------------------------
    for p in sensors:
        if not p.online:
            print("Sensor %s is offline." % p.name)
            continue
        print("Sensor %s: temperature %s, humidty %s" % (p.name, p.temperature, p.humidity))

    # At this point, we are all done playing with the library, so we gracefully disconnect and clean resources.
    print("We are done playing. Cleaning resources...")
    manager.stop()

    print("Bye bye!")
