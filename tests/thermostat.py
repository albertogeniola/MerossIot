import os

from meross_iot.cloud.devices.subdevices.thermostats import ValveSubDevice, ThermostatV3Mode
from meross_iot.manager import MerossManager
from meross_iot.meross_event import MerossEventType

EMAIL = os.environ.get('MEROSS_EMAIL') or "YOUR_MEROSS_CLOUD_EMAIL"
PASSWORD = os.environ.get('MEROSS_PASSWORD') or "YOUR_MEROSS_CLOUD_PASSWORD"


if __name__ == '__main__':
    # Initiates the Meross Cloud Manager. This is in charge of handling the communication with the remote endpoint
    manager = MerossManager(meross_email=EMAIL, meross_password=PASSWORD)

    # Register event handlers for the manager...
    # manager.register_event_handler(event_handler)

    # Starts the manager
    manager.start()
    thermostat = manager.get_devices_by_kind(ValveSubDevice)[0]  # type: ValveSubDevice

    print("Current mode %s" % thermostat.mode)
    thermostat.set_mode(ThermostatV3Mode.COOL)
    print("Current mode %s" % thermostat.mode)

    print("Current room temperature fs" % thermostat.room_temperature)
    thermostat.set_target_temperature(10)

    manager.stop()
    print("Bye bye!")
