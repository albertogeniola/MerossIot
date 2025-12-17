from typing import Any, Generator, Dict

import pytest
from _pytest import assertion
from setuptools.dist import assert_bool

from meross_iot.controller.mixins.diffuser_light import DiffuserLightMixin
from meross_iot.manager import MerossManager
from meross_iot.model.enums import Namespace, DiffuserLightMode
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


async def test_async_diffuser_light_get_mode(device: DiffuserLightMixin,
                                  handle_update_fixture_getter,
                                  manager_mock,
                                  replacer_mock: Dict[str, Any]):
    """
    Tests the capabilities of getting diffuser light mode.
    """
    # Simulate updating the device state. The fixture reports a mod150 with an OFF light state, with fixed RGB set to
    # RED (16711680).
    await device.async_handle_update(namespace=Namespace.SYSTEM_ALL,
                                     data=handle_update_fixture_getter("mod150", replacer_mock))

    # The first state must be OFF
    assert device.diffuser_light_get_mode() == DiffuserLightMode.FIXED_RGB


async def test_diffuser_light_get_brightness(device: DiffuserLightMixin,
                                             handle_update_fixture_getter,
                                             replacer_mock: Dict[str, Any]):
    """
    Tests the capabilities of getting diffuser light brightness.
    """
    await device.async_handle_update(namespace=Namespace.SYSTEM_ALL,
                                     data=handle_update_fixture_getter("mod150", replacer_mock))
    assert device.diffuser_light_get_brightness() == 100


async def test_diffuser_light_get_rgb_color(device: DiffuserLightMixin,
                                            handle_update_fixture_getter,
                                            replacer_mock: Dict[str, Any]):
    """
    Tests the capabilities of getting diffuser light RGB color.
    """
    await device.async_handle_update(namespace=Namespace.SYSTEM_ALL,
                                     data=handle_update_fixture_getter("mod150", replacer_mock))
    assert device.diffuser_light_get_rgb_color() == (255, 0, 0)


async def test_async_diffuser_light_set_rgb_color(device: DiffuserLightMixin,
                                                  handle_update_fixture_getter,
                                                  replacer_mock: Dict[str, Any]):
    """
    Tests the capabilities of setting diffuser light RGB color.
    """
    await device.async_handle_update(namespace=Namespace.SYSTEM_ALL,
                                     data=handle_update_fixture_getter("mod150", replacer_mock))

    await device.async_diffuser_light_set_rgb_color(rgb=(0, 255, 0))
    assert device.diffuser_light_get_rgb_color() == (0, 255, 0)
    assert device.diffuser_light_get_mode() == DiffuserLightMode.FIXED_RGB
    assert device.diffuser_light_get_is_on() is True


async def test_async_diffuser_light_set_temperature(device: DiffuserLightMixin,
                                                    handle_update_fixture_getter,
                                                    replacer_mock: Dict[str, Any]):
    """
    Tests the capabilities of setting diffuser light temperature.
    """
    await device.async_handle_update(namespace=Namespace.SYSTEM_ALL,
                                     data=handle_update_fixture_getter("mod150", replacer_mock))

    await device.async_diffuser_light_set_temperature(brightness=50)
    assert device.diffuser_light_get_brightness() == 50
    assert device.diffuser_light_get_mode() == DiffuserLightMode.FIXED_LUMINANCE
    assert device.diffuser_light_get_is_on() is True


async def test_async_diffuser_light_set_rotating_colors(device: DiffuserLightMixin,
                                                        handle_update_fixture_getter,
                                                        replacer_mock: Dict[str, Any]):
    """
    Tests the capabilities of setting diffuser light rotating colors.
    """
    await device.async_handle_update(namespace=Namespace.SYSTEM_ALL,
                                     data=handle_update_fixture_getter("mod150", replacer_mock))

    await device.async_diffuser_light_set_rotating_colors(brightness=50)
    assert device.diffuser_light_get_brightness() == 50
    assert device.diffuser_light_get_mode() == DiffuserLightMode.ROTATING_COLORS
    assert device.diffuser_light_get_is_on() is True


async def test_async_diffuser_light_turn_on_off(device: DiffuserLightMixin,
                                                handle_update_fixture_getter,
                                                replacer_mock: Dict[str, Any]):
    """
    Tests the capabilities of turning on/off the diffuser light.
    """
    await device.async_handle_update(namespace=Namespace.SYSTEM_ALL,
                                     data=handle_update_fixture_getter("mod150", replacer_mock))

    # Ensure it is off initially (from fixture)
    assert device.diffuser_light_get_is_on() is False

    # Turn on
    await device.async_diffuser_light_turn_on()
    assert device.diffuser_light_get_is_on() is True

    # Turn off
    await device.async_diffuser_light_turn_off()
    assert device.diffuser_light_get_is_on() is False


async def test_invalid_channel_handling(device: DiffuserLightMixin,
                                        handle_update_fixture_getter,
                                        replacer_mock: Dict[str, Any]):
    """
    Tests that invalid channels raise ValueError.
    """
    await device.async_handle_update(namespace=Namespace.SYSTEM_ALL,
                                     data=handle_update_fixture_getter("mod150", replacer_mock))

    # Test invalid channel for get_mode
    with pytest.raises(ValueError):
        device.diffuser_light_get_mode(channel=99)

    # Test invalid channel for get_brightness
    with pytest.raises(ValueError):
        device.diffuser_light_get_brightness(channel=99)

    # Test invalid channel for get_rgb_color
    with pytest.raises(ValueError):
        device.diffuser_light_get_rgb_color(channel=99)

    # Test invalid channel for get_is_on
    with pytest.raises(ValueError):
        device.diffuser_light_get_is_on(channel=99)

    # Test invalid channel for set_light_mode (via turn_on)
    with pytest.raises(ValueError):
        await device.async_diffuser_light_turn_on(channel=99)




