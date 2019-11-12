from meross_iot.manager import MerossManager
from meross_iot.meross_event import MerossEventType
from meross_iot.cloud.devices.hubs import GenericHub
import os

EMAIL = os.environ.get('MEROSS_EMAIL') or "YOUR_MEROSS_CLOUD_EMAIL"
PASSWORD = os.environ.get('MEROSS_PASSWORD') or "YOUR_MEROSS_CLOUD_PASSWORD"


def event_handler(eventobj):
    if eventobj.event_type == MerossEventType.DEVICE_HUB_SUBDEVICE_STATE:
        print("HubState is now %s" % eventobj.state)


if __name__ == '__main__':
    # Initiates the Meross Cloud Manager. This is in charge of handling the communication with the remote endpoint
    manager = MerossManager(meross_email=EMAIL, meross_password=PASSWORD)

    # Register event handlers for the manager...
    manager.register_event_handler(event_handler)

    # Starts the manager
    manager.start()
    hub_devices = manager.get_devices_by_kind(GenericHub)

    print("All the hubs I found:")
    for h in hub_devices:
        print(h)

    print("You can now play with the thermostat and see if the state is propagated here. Once you are done,"
          " press any key to exit")
    data = input()

    # At this point, we are all done playing with the library, so we gracefully disconnect and clean resources.
    print("We are done playing. Cleaning resources...")
    manager.stop()

    print("Bye bye!")