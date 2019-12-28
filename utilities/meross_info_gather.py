import logging
from os import path
from zipfile import ZipFile

from meross_iot.cloud.device import AbstractMerossDevice
from meross_iot.cloud.devices.hubs import GenericHub
from meross_iot.logger import h
from meross_iot.manager import MerossManager

ROOT_LOG_FILE = 'root.log'
INFO_LOG_FILE = 'info.log'

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

root = logging.getLogger()
root.setLevel(logging.DEBUG)
rhandler = logging.FileHandler(mode='w', filename=ROOT_LOG_FILE)
rhandler.setFormatter(formatter)
rhandler.setLevel(logging.DEBUG)
root.addHandler(rhandler)

l = root.getChild("InfoGather")
l.setLevel(logging.DEBUG)
lhandler = logging.FileHandler(mode='w', filename=INFO_LOG_FILE)
lhandler.setFormatter(formatter)
l.addHandler(lhandler)
h.setLevel(logging.ERROR)


def describe_device(
        d,  # type: AbstractMerossDevice
        manager
                    ):

    l.info("Found device {name}, type: {type}, uuid: {uuid}, firmware: {firmware}, hardware: {hardware}".format(
           name=d.name, type=d.type, uuid=d.uuid, firmware=d.fwversion, hardware=d.hwversion))

    # Gathering status
    sysdata = d.get_sys_data()
    l.info("GET ALL on {uuid} = {sysdata}".format(uuid=d.uuid, sysdata=sysdata))

    # Gathering abilities
    abilities = d.get_abilities()
    l.info("GET ABILITIES on {uuid} = {abilities}".format(uuid=d.uuid, abilities=abilities))

    if isinstance(d, GenericHub):
        subdevices = manager._http_client.list_hub_subdevices(d.uuid)
        l.info("SUBDEVICES of hub {uuid} = {subdevices}".format(uuid=d.uuid, subdevices=subdevices))


def main():
    print("Welcome to the InfoGather software. This python script will gather some useful information about your "
          "Meross devices. All the collected information will be zipped into a zip archive. "
          "You could share such zip file with the developers to help them add support for your device. "
          "Although this utility won't collect your email/password, we recommend you to change "
          "your Meross account password to a temporary one before using this software. Once you are done, "
          "you can restore back your original password. By doing so, you are 100% sure you are not leaking any "
          "real password to the developers.")
    email = input("Please specify your meross email: ")
    email = email.strip()
    password = input("Please specify your meross password: ")
    password = password.strip()
    devices = []
    manager = None

    try:
        manager = MerossManager(meross_email=email, meross_password=password)
        client = manager._http_client
        print("# Collecting devices via HTTP api...")

        devices = client.list_devices()
        l.info("DEVICE LISTING VIA HTTP: %s" % devices)
    except:
        print("An error occurred while retrieving Meross devices.")
        exit(1)

    print("# Starting manager...")
    manager.start()

    print("# Gathering info about supported devices...")
    devices = manager.get_supported_devices()
    for d in devices:
        describe_device(d, manager)

    print("# OK. You can now play with the Meross official APP with your devices to trigger some actions. Hopefully"
          " this program will be able to collect necessary data to help the developers implement its support.")
    print("Once done, simply press ENTER and the program will stop gathering information and return.")
    input("Press ENTER to stop recording data and exit")

    print("Collecting logs...")
    zipObj = ZipFile('data.zip', 'w')
    zipObj.write(ROOT_LOG_FILE)
    zipObj.write(INFO_LOG_FILE)
    zipObj.close()

    print("A zipfile has been created containing the logs collected during this execution. "
          "It is located in {path}.".format(path=path.abspath(zipObj.filename)))
    print("Thanks for helping the Meross community!")


if __name__ == '__main__':
    main()

