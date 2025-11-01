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
@pytest.mark.asyncio
async def test_subdevice_alarm_push_notification(device: AlarmMixin,
                                                 push_notification_fixture: Callable[[str, Dict], Dict[str, Any]],
                                                 uuid_mock: str,
                                                 sub_uuid_mock: str):
    # Prepare the push notification object
    payload = push_notification_fixture("alarm", {"uuid": uuid_mock, "sub_uuid": sub_uuid_mock})

    # Ensure clean initial state
    assert len(device.alarm_last_events) == 0

    # Simulate receiving it
    await device.async_dispatch_push_notification(namespace=Namespace.CONTROL_ALARM, data=payload)
    assert len(device.alarm_last_events) == 1
