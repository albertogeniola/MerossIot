from typing import Any, Generator, Dict

import pytest

from meross_iot.controller.mixins.dnd import SystemDndMixin
from meross_iot.manager import MerossManager
from meross_iot.model.enums import DNDMode


@pytest.fixture()
def device(manager_mock: MerossManager, replacer_mock: Dict[str, Any]) -> Generator[SystemDndMixin, Any, None]:
    dnd_mock_device = SystemDndMixin(device_uuid=replacer_mock["UUID"], manager=manager_mock)
    yield dnd_mock_device


async def test_async_system_dnd_fetch_mode(device: SystemDndMixin,
                                           manager_mock,
                                           replacer_mock: Dict[str, Any]):
    """
    Test async_system_dnd_fetch_mode functionality
    :param device:
    :param manager_mock:
    :param replacer_mock:
    :return:
    """
    # Simulate updating the device state
    with manager_mock.mock_execute_command("GET", "SYSTEM_DND_MODE", replacer_mock):
        mode = await device.async_system_dnd_fetch_mode()

    # Verify the result
    assert mode == DNDMode.DND_DISABLED


async def test_async_system_dnd_set_mode(device: SystemDndMixin,
                                         manager_mock,
                                         replacer_mock: Dict[str, Any]):
    """
    Test async_system_dnd_set_mode functionality
    :param device:
    :param manager_mock:
    :param replacer_mock:
    :return:
    """
    # Simulate updating the device state
    with manager_mock.mock_execute_command("SET", "SYSTEM_DND_MODE", replacer_mock):
        await device.async_system_dnd_set_mode(DNDMode.DND_ENABLED)

    # Since we don't cache state, we can't verify local state update.
    # We just verify the command execution (which is implicitly done by mock_execute_command context manager finding the fixture)
