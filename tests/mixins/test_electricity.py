from typing import Any, Generator, Dict
import pytest
from meross_iot.controller.mixins.electricity import ElectricityMixin
from meross_iot.manager import MerossManager
from meross_iot.model.plugin.power import PowerInfo

@pytest.fixture()
def device(manager_mock: MerossManager, replacer_mock: Dict[str, Any]) -> Generator[ElectricityMixin, Any, None]:
    device_mock = ElectricityMixin(device_uuid=replacer_mock["UUID"], manager=manager_mock)
    yield device_mock

from meross_iot.model.enums import Namespace

async def test_async_electricity_fetch_instant_metrics(device: ElectricityMixin,
                                                       manager_mock,
                                                       handle_update_fixture_getter,
                                                       replacer_mock: Dict[str, Any]):
    """
    Test async_electricity_fetch_instant_metrics functionality
    """
    # Simulate device coming online
    await device.async_handle_update(namespace=Namespace.SYSTEM_ALL,
                                     data=handle_update_fixture_getter("mss310", replacer_mock))

    # Simulate updating the device state via GET request
    with manager_mock.mock_execute_command("GET", "CONTROL_ELECTRICITY", replacer_mock):
        power_info = await device.async_electricity_fetch_instant_metrics()

    assert power_info is not None
    assert isinstance(power_info, PowerInfo)
    # Based on our fixture: current=0/1000=0.0, voltage=2293/10=229.3, power=0/1000=0.0
    assert power_info.current == 0.0
    assert power_info.voltage == 229.3
    assert power_info.power == 0.0

async def test_electricity_get_last_sample(device: ElectricityMixin,
                                           manager_mock,
                                           handle_update_fixture_getter,
                                           replacer_mock: Dict[str, Any]):
    """
    Test electricity_get_last_sample functionality (caching)
    """
    # Simulate device coming online
    await device.async_handle_update(namespace=Namespace.SYSTEM_ALL,
                                     data=handle_update_fixture_getter("mss310", replacer_mock))

    # Initially should be None
    assert device.electricity_get_last_sample() is None

    # Fetch data first
    with manager_mock.mock_execute_command("GET", "CONTROL_ELECTRICITY", replacer_mock):
        await device.async_electricity_fetch_instant_metrics()

    # Now it should be cached
    cached_info = device.electricity_get_last_sample()
    assert cached_info is not None
    assert cached_info.power == 0.0
