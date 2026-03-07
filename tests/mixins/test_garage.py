from datetime import datetime
from typing import Any, Dict, Generator, Callable
from unittest.mock import MagicMock, AsyncMock, patch

import pytest
from meross_iot.controller.device import ChannelInfo
from meross_iot.controller.mixins.garage import GarageOpenerMixin
from meross_iot.manager import MerossManager
from meross_iot.model.enums import Namespace


@pytest.fixture()
def device(manager_mock: MerossManager, replacer_mock: Dict[str, Any]) -> Generator[GarageOpenerMixin, Any, None]:
    dev = GarageOpenerMixin(device_uuid=replacer_mock["UUID"], manager=manager_mock)
    yield dev
    

async def test_garage_opener_open_close(device: GarageOpenerMixin, manager_mock, replacer_mock):
    # Simulate correct initialization
    device._last_full_update_ts = datetime.now().timestamp()
    
    # Test open
    with manager_mock.mock_execute_command("SET", "GARAGE_DOOR_STATE", replacer_mock):
        await device.async_garage_opener_open(channel=0)
        
    # Test close
    with manager_mock.mock_execute_command("SET", "GARAGE_DOOR_STATE", replacer_mock):
        await device.async_garage_opener_close(channel=0)


async def test_garage_opener_push_notification(device: GarageOpenerMixin, push_notification_fixture: Callable[[str, Dict], Dict[str, Any]], replacer_mock: Dict[str, Any]):
    # Setup state to closed
    device._last_full_update_ts = datetime.now().timestamp()
    
    # Prepare push notification for closed state (as per fixture garage_opener-closed.json)
    payload = push_notification_fixture("garage_opener-closed", replacer_mock)
    
    # Based on fixture content: open=0 (closed)
    await device._async_handle_push_notification(namespace=Namespace.GARAGE_DOOR_STATE, data=payload)
    
    assert device.garage_opener_is_open(channel=2) is False


async def test_garage_opener_system_all_update(device: GarageOpenerMixin, handle_update_fixture_getter: Callable[[str, Dict], Dict[str, Any]], replacer_mock: Dict[str, Any]):
    # Simulate a full update
    payload = handle_update_fixture_getter("msg200", replacer_mock)
    await device.async_handle_update(namespace=Namespace.SYSTEM_ALL, data=payload)
    
    # Check checks. msg200.json has "garageDoor": [{"channel": 1, "open": 1, ...}] -> open=True
    assert device.garage_opener_is_open(channel=1) is True


async def test_garage_opener_config_push_notification(device: GarageOpenerMixin, push_notification_fixture: Callable[[str, Dict], Dict[str, Any]], replacer_mock: Dict[str, Any]):
    # Test MULTIPLECONFIG push
    device._last_full_update_ts = datetime.now().timestamp()
    payload = push_notification_fixture("garage_opener-config", replacer_mock)
    handled = await device._async_handle_push_notification(namespace=Namespace.GARAGE_DOOR_MULTIPLECONFIG, data=payload)
    assert handled
    config = device.garage_opener_get_config(channel=0)
    assert config is not None
    assert config['signalDuration'] == 1000

async def test_garage_opener_update(device: GarageOpenerMixin, manager_mock, replacer_mock):
    device._last_full_update_ts = datetime.now().timestamp()
    with manager_mock.mock_execute_command("GET", "GARAGE_DOOR_MULTIPLECONFIG", replacer_mock):
        await device.async_update()
    
    config = device.garage_opener_get_config(channel=1)
    assert config is not None
    assert config['signalClose'] == 2000

async def test_garage_opener_default_channel(device: GarageOpenerMixin, manager_mock, replacer_mock):
    device._last_full_update_ts = datetime.now().timestamp()
    # Test open with channel=None (should default to 0 since len(channels)=1)
    with manager_mock.mock_execute_command("SET", "GARAGE_DOOR_STATE", replacer_mock):
        await device.async_garage_opener_open(channel=None)

async def test_garage_opener_multiple_channels(manager_mock, replacer_mock):
    # Use patch to prevent BaseDevice.__init__ from resetting dev._channels to []
    with patch('meross_iot.controller.mixins.garage.BaseDevice.__init__', return_value=None):
        dev = GarageOpenerMixin.__new__(GarageOpenerMixin)
        dev._channels = [ChannelInfo(index=0), ChannelInfo(index=1)]
        dev.__garage_opener_open_state_by_channel = {}
        dev.__garage_opener_config_state_by_channel = {}
        dev.__init__(device_uuid=replacer_mock["UUID"], manager=manager_mock)
    
    dev.check_full_update_done = MagicMock()
    dev._last_full_update_ts = datetime.now().timestamp()
    assert dev.garage_opener_is_open(channel=None) is None

async def test_garage_opener_set_config(device: GarageOpenerMixin, manager_mock, replacer_mock):
    device._last_full_update_ts = datetime.now().timestamp()
    device._GarageOpenerMixin__garage_opener_config_state_by_channel[1] = {'channel': 1}
    with manager_mock.mock_execute_command("SET", "GARAGE_DOOR_MULTIPLECONFIG", replacer_mock):
        await device.async_garage_opener_set_config(
            channel=1,
            door_enable=True,
            door_close_duration_mesec=15000,
            door_open_duration_mesec=14000,
            close_signal_mesec=2000,
            open_signal_mesec=1000,
            buzzer_enable=False
        )
        
async def test_garage_opener_set_config_edge_cases(device: GarageOpenerMixin, manager_mock, replacer_mock):
    device._last_full_update_ts = datetime.now().timestamp()
    
    # Test setting config for a channel that isn't returned from the server (e.g., config array misses channel key)
    # The current SET fixture returns channel 1.
    # We call set_config for a different channel, and the server fixture returns channel 1 config.
    # This invokes the `elif self.__garage_opener_config_state_by_channel.get(target_channel) is not None:`
    # line 151-152
    with patch.object(device, '_execute_command', return_value={'config': [{'channel': 1, 'doorEnable': 1}]}):
        # Seed channel 2 with initial dict to pass the "is not None" check
        device._GarageOpenerMixin__garage_opener_config_state_by_channel[2] = {"channel": 2, "doorEnable": 1}
        # Call set_config passing channel=2, which creates a door_config payload for channel=2 
        # but the mock returns channel=1 in the response
        await device.async_garage_opener_set_config(
            channel=2,
            door_enable=False
        )
        # Verify the local state was updated with door_config because the server response didn't contain channel 2
        config2 = device.garage_opener_get_config(channel=2)
        assert config2 is not None
        assert config2['channel'] == 2
        assert config2['doorEnable'] == 0
        

