from typing import Any, Generator, Dict

import pytest

from meross_iot.controller.mixins.consumption import ConsumptionXMixin, ConsumptionMixin
from meross_iot.manager import MerossManager
from meross_iot.model.enums import Namespace
from meross_iot.model.exception import OutOfSyncError


@pytest.fixture()
def device_x(manager_mock: MerossManager, replacer_mock: Dict[str, Any]) -> Generator[ConsumptionXMixin, Any, None]:
    dev = ConsumptionXMixin(device_uuid=replacer_mock["UUID"], manager=manager_mock)
    yield dev


@pytest.fixture()
def device(manager_mock: MerossManager, replacer_mock: Dict[str, Any]) -> Generator[ConsumptionMixin, Any, None]:
    dev = ConsumptionMixin(device_uuid=replacer_mock["UUID"], manager=manager_mock)
    yield dev


# We are not testing push notifications here, as the CONSUMPTION
# mixin seems not to send any


async def test_refresh_last_event_x(device_x: ConsumptionXMixin,
                                    manager_mock,
                                    handle_update_fixture_getter,
                                    replacer_mock: Dict[str, Any]):
    """
    Tests the capabilities of retrieving last consumption data.
    :param device:
    :param replacer_mock:
    :return:
    """
    # Simulate updating the device state
    await device_x.async_handle_update(namespace=Namespace.SYSTEM_ALL,
                                       data=handle_update_fixture_getter("mss310", replacer_mock))

    # Simulate updating the device state
    with manager_mock.mock_execute_command("GET", "CONTROL_CONSUMPTIONX", replacer_mock):
        await device_x.async_consumption_fetch_summary()

    # Make sure we now have the event.
    assert len(device_x.consumption_daily_summary) == 30


async def test_update_x(device_x: ConsumptionXMixin,
                        manager_mock,
                        handle_update_fixture_getter,
                        replacer_mock: Dict[str, Any]):
    """
    Test async_update functionality
    :param device:
    :param manager_mock:
    :param replacer_mock:
    :return:
    """
    # Simulate updating the device state
    await device_x.async_handle_update(namespace=Namespace.SYSTEM_ALL,
                                       data=handle_update_fixture_getter("mss310", replacer_mock))

    # Simulate updating the device state
    with manager_mock.mock_execute_command("GET", "CONTROL_CONSUMPTIONX", replacer_mock):
        await device_x.async_update()

    # Make sure we now have the event.
    assert len(device_x.consumption_daily_summary) == 30


async def test_refresh_last_event(device: ConsumptionMixin,
                                  manager_mock,
                                  handle_update_fixture_getter,
                                  replacer_mock: Dict[str, Any]):
    """
    Tests the capabilities of retrieving last consumption data.
    :param device:
    :param replacer_mock:
    :return:
    """
    # Simulate updating the device state
    await device.async_handle_update(namespace=Namespace.SYSTEM_ALL,
                                       data=handle_update_fixture_getter("mss310", replacer_mock))

    # Simulate updating the device state
    with manager_mock.mock_execute_command("GET", "CONTROL_CONSUMPTION", replacer_mock):
        await device.async_consumption_fetch_summary()

    # Make sure we now have the event.
    assert len(device.consumption_daily_summary) == 30


async def test_update(device: ConsumptionMixin,
                      manager_mock,
                      handle_update_fixture_getter,
                      replacer_mock: Dict[str, Any]):
    """
    Test async_update functionality
    :param device:
    :param manager_mock:
    :param replacer_mock:
    :return:
    """
    # Simulate updating the device state
    await device.async_handle_update(namespace=Namespace.SYSTEM_ALL,
                                       data=handle_update_fixture_getter("mss310", replacer_mock))

    # Simulate updating the device state
    with manager_mock.mock_execute_command("GET", "CONTROL_CONSUMPTION", replacer_mock):
        await device.async_update()

    # Make sure we now have the event.
    assert len(device.consumption_daily_summary) == 30
