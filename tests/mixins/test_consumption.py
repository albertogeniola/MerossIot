from typing import Any, Generator, Dict, Callable

import pytest

from meross_iot.controller.mixins.consumption import ConsumptionXMixin
from meross_iot.manager import MerossManager
from meross_iot.model.enums import Namespace


@pytest.fixture()
def device(manager_mock: MerossManager, replacer_mock: Dict[str, Any]) -> Generator[ConsumptionXMixin, Any, None]:
    alarm_mock_device = ConsumptionXMixin(device_uuid=replacer_mock["UUID"], manager=manager_mock)
    yield alarm_mock_device

# We are not testing push notifications here, as the CONSUMPTION
# mixin seems not to send any

async def test_refresh_last_event(device: ConsumptionXMixin,
                                  manager_mock,
                                  replacer_mock: Dict[str, Any]):
    """
    Tests the capabilities of retrieving last consumption data.
    :param device:
    :param replacer_mock:
    :return:
    """
    # Before initialization, the summary must be empty
    assert len(device.consumption_daily_summary) == 0

    # Simulate updating the device state
    with manager_mock.mock_execute_command("GET", "CONTROL_CONSUMPTIONX", replacer_mock):
        await device.async_consumption_fetch_summary()

    # Make sure we now have the event.
    assert len(device.consumption_daily_summary) == 30  # We expect 30 samples


async def test_update(device: ConsumptionXMixin,
                      manager_mock,
                      replacer_mock: Dict[str, Any]):
    """
    Test async_update functionality
    :param device:
    :param manager_mock:
    :param replacer_mock:
    :return:
    """
    # Before initialization, the summary must be empty
    assert len(device.consumption_daily_summary) == 0

    # Simulate updating the device state
    with manager_mock.mock_execute_command("GET", "CONTROL_CONSUMPTIONX", replacer_mock):
        await device.async_consumption_fetch_summary()

    # Make sure we now have the event.
    assert len(device.consumption_daily_summary) == 30  # We expect 30 samples
