from typing import Any, Generator, Dict, Callable

import pytest

from meross_iot.controller.mixins.alarm import AlarmMixin
from meross_iot.manager import MerossManager
from meross_iot.model.enums import Namespace


@pytest.fixture()
def device(manager_mock: MerossManager, uuid_mock: str) -> Generator[AlarmMixin, Any, None]:
    alarm_mock_device = AlarmMixin(device_uuid=uuid_mock, manager=manager_mock)
    yield alarm_mock_device


# Ensure push notifications are handled correctly
async def test_subdevice_alarm_push_notification(device: AlarmMixin,
                                                 push_notification_fixture: Callable[[str, Dict], Dict[str, Any]],
                                                 uuid_mock: str,
                                                 sub_uuid_mock: str):
    """
    Tests the push notification handling feature
    :param device:
    :param push_notification_fixture:
    :param uuid_mock:
    :param sub_uuid_mock:
    :return:
    """
    # Prepare the push notification object
    payload = push_notification_fixture("alarm", {"uuid": uuid_mock, "sub_uuid": sub_uuid_mock})

    # Ensure clean initial state
    assert len(device.alarm_last_events) == 0

    # Simulate receiving it
    await device.async_dispatch_push_notification(namespace=Namespace.CONTROL_ALARM, data=payload)
    assert len(device.alarm_last_events) == 1


async def test_refresh_last_event(device: AlarmMixin,
                                  manager_mock,
                                  uuid_mock: str,
                                  sub_uuid_mock: str):
    """
    Tests the capabilities of retrieving last alarm event.
    :param device:
    :param uuid_mock:
    :param sub_uuid_mock:
    :return:
    """
    # Before initialization, the event list must be empty
    assert len(device.alarm_last_events) == 0

    # Simulate updating the device state
    with manager_mock.mock_execute_command("GET", "CONTROL_ALARM", {"uuid": uuid_mock}):
        await device.alarm_refresh_last_event()

    # Make sure we now have the event.
    assert len(device.alarm_last_events) == 1


async def test_update(device: AlarmMixin,
                      manager_mock,
                      uuid_mock: str,
                      sub_uuid_mock: str):
    """
    Test async_update functionality
    :param device:
    :param manager_mock:
    :param uuid_mock:
    :param sub_uuid_mock:
    :return:
    """
    # Before initialization, the event list must be empty
    assert len(device.alarm_last_events) == 0

    # Simulate updating the device state
    with manager_mock.mock_execute_command("GET", "CONTROL_ALARM", {"uuid": uuid_mock}):
        await device.async_update()

    # Make sure we now have the event.
    assert len(device.alarm_last_events) == 1
