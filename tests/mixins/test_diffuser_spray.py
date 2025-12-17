from typing import Any, Generator, Dict

import pytest

from meross_iot.controller.mixins.diffuser_spray import DiffuserSprayMixin
from meross_iot.manager import MerossManager
from meross_iot.model.enums import Namespace, DiffuserSprayMode


@pytest.fixture()
def device(manager_mock: MerossManager, replacer_mock: Dict[str, Any]) -> Generator[DiffuserSprayMixin, Any, None]:
    dev = DiffuserSprayMixin(device_uuid=replacer_mock["UUID"], manager=manager_mock)
    yield dev


async def test_async_handle_update(device: DiffuserSprayMixin,
                                   handle_update_fixture_getter,
                                   replacer_mock: Dict[str, Any]):
    """
    Test async_update functionality
    :param device:
    :param replacer_mock:
    :return:
    """
    # Simulate updating the device state
    await device.async_handle_update(namespace=Namespace.SYSTEM_ALL,
                                     data=handle_update_fixture_getter("mod150", replacer_mock))

    # The mocked system_update should produce "OFF" state (mode 2)
    assert device.diffuser_spray_get_mode() == DiffuserSprayMode.OFF


async def test_async_handle_push_notification(device: DiffuserSprayMixin,
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
    # Simulate updating the device state. This should produce an OFF state
    await device.async_handle_update(namespace=Namespace.SYSTEM_ALL,
                                     data=handle_update_fixture_getter("mod150", replacer_mock))
    assert device.diffuser_spray_get_mode() == DiffuserSprayMode.OFF

    # Simulate a push notification for STRONG state (mode 1)
    await device.async_dispatch_push_notification(namespace=Namespace.DIFFUSER_SPRAY,
                                     data=push_notification_fixture("diffuser_spray-strong", replacer_mock))

    # Ensure we now have a STRONG state
    assert device.diffuser_spray_get_mode() == DiffuserSprayMode.STRONG


async def test_async_diffuser_spray_set_mode(device: DiffuserSprayMixin,
                                  handle_update_fixture_getter,
                                  manager_mock,
                                  replacer_mock: Dict[str, Any]):
    """
    Tests the capabilities of setting diffuser spray mode.
    :param device:
    :param replacer_mock:
    :return:
    """
    # Simulate updating the device state. This should produce an OFF state
    await device.async_handle_update(namespace=Namespace.SYSTEM_ALL,
                                     data=handle_update_fixture_getter("mod150", replacer_mock))

    # The first state must be OFF
    assert device.diffuser_spray_get_mode() == DiffuserSprayMode.OFF

    # Let's set the state to STRONG
    with manager_mock.mock_execute_command("SET", "CONTROL_DIFFUSER_SPRAY_STRONG", replacer_mock):
        await device.async_diffuser_spray_set_mode(mode=DiffuserSprayMode.STRONG)
        assert device.diffuser_spray_get_mode() == DiffuserSprayMode.STRONG


async def test_invalid_channel_handling(device: DiffuserSprayMixin,
                                        handle_update_fixture_getter,
                                        replacer_mock: Dict[str, Any]):
    """
    Tests that invalid channels raise ValueError.
    """
    await device.async_handle_update(namespace=Namespace.SYSTEM_ALL,
                                     data=handle_update_fixture_getter("mod150", replacer_mock))

    # Test invalid channel for get_mode
    with pytest.raises(ValueError):
        device.diffuser_spray_get_mode(channel=99)

    # Test invalid channel for set_mode
    with pytest.raises(ValueError):
        await device.async_diffuser_spray_set_mode(mode=DiffuserSprayMode.STRONG, channel=99)




