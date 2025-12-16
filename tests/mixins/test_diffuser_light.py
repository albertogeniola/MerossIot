from typing import Any, Generator, Dict

import pytest

from meross_iot.controller.mixins.diffuser_light import DiffuserLightMixin
from meross_iot.manager import MerossManager
from meross_iot.model.enums import Namespace
from meross_iot.model.exception import OutOfSyncError


@pytest.fixture()
def device(manager_mock: MerossManager, replacer_mock: Dict[str, Any]) -> Generator[DiffuserLightMixin, Any, None]:
    dev = DiffuserLightMixin(device_uuid=replacer_mock["UUID"], manager=manager_mock)
    yield dev


async def test_async_handle_update(device: DiffuserLightMixin,
                                   handle_update_fixture_getter,
                                   replacer_mock: Dict[str, Any]):
    """
    Test async_update functionality
    :param device:
    :param replacer_mock:
    :return:
    """
    # Attempting to access before async_update must trigger OutOfSync error
    with pytest.raises(OutOfSyncError):
        assert device.diffuser_light_get_is_on() is None

    # Simulate updating the device state
    await device.async_handle_update(namespace=Namespace.SYSTEM_ALL,
                                     data=handle_update_fixture_getter("mod150", replacer_mock))

    # The mocked system_update should produce "off" state
    assert device.diffuser_light_get_is_on() == False


async def test_async_handle_push_notification(device: DiffuserLightMixin,
                                              handle_update_fixture_getter,
                                              push_notification_fixture,
                                              replacer_mock: Dict[str, Any]):
    """
    Test push notification functionality
    :param device:
    :param handle_update_fixture_getter:
    :param push_notification_fixture:
    :param replacer_mock:
    :return:
    """
    # Simulate updating the device state. This should produce a OFF state
    await device.async_handle_update(namespace=Namespace.SYSTEM_ALL,
                                     data=handle_update_fixture_getter("mod150", replacer_mock))
    assert device.diffuser_light_get_is_on() == False

    # Simulate a push notification for OFF state
    await device.async_dispatch_push_notification(namespace=Namespace.DIFFUSER_LIGHT,
                                     data=push_notification_fixture("diffuser_light-off", replacer_mock))

    # Ensure we now have a ON state
    assert device.diffuser_light_get_is_on() == True
