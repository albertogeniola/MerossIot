from typing import Any, Generator, Dict, Callable

import pytest

from meross_iot.controller.mixins.alarm import AlarmMixin
from meross_iot.manager import MerossManager
from meross_iot.model.enums import Namespace


@pytest.fixture()
def device(manager_mock: MerossManager, replacer_mock: Dict[str, Any]) -> Generator[AlarmMixin, Any, None]:
    alarm_mock_device = AlarmMixin(device_uuid=replacer_mock["UUID"], manager=manager_mock)
    yield alarm_mock_device


# Ensure push notifications are handled correctly
async def test_subdevice_alarm_push_notification(device: AlarmMixin,
                                                 push_notification_fixture: Callable[[str, Dict], Dict[str, Any]],
                                                 replacer_mock: Dict[str, Any]):
    """
    Tests the push notification handling feature
    :param device:
    :param push_notification_fixture:
    :param replacer_mock:
    :return:
    """
    # Prepare the push notification object
    payload = push_notification_fixture("alarm", replacer_mock)

    # Ensure clean initial state
    assert len(device.alarm_last_events) == 0

    # Simulate receiving it
    await device.async_dispatch_push_notification(namespace=Namespace.CONTROL_ALARM, data=payload)
    assert len(device.alarm_last_events) == 1


async def test_refresh_last_event(device: AlarmMixin,
                                  manager_mock,
                                  replacer_mock: Dict[str, Any]):
    """
    Tests the capabilities of retrieving last alarm event.
    :param device:
    :param replacer_mock:
    :return:
    """
    # Before initialization, the event list must be empty
    assert len(device.alarm_last_events) == 0

    # Simulate updating the device state
    with manager_mock.mock_execute_command("GET", "CONTROL_ALARM", replacer_mock):
        await device.async_alarm_fetch_events()

    # Make sure we now have the event.
    assert len(device.alarm_last_events) == 1


async def test_update(device: AlarmMixin,
                      manager_mock,
                      replacer_mock: Dict[str, Any]):
    """
    Test async_update functionality
    :param device:
    :param manager_mock:
    :param replacer_mock:
    :return:
    """
    # Before initialization, the event list must be empty
    assert len(device.alarm_last_events) == 0

    # Simulate updating the device state
    with manager_mock.mock_execute_command("GET", "CONTROL_ALARM", replacer_mock):
        await device.async_update()

    # Make sure we now have the event.
    assert len(device.alarm_last_events) == 1
