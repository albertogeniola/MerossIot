import json
import os
import string
import unittest.mock
from typing import Dict, Any
from unittest.mock import MagicMock

import pytest

from meross_iot.manager import MerossManager
from meross_iot.model.enums import Namespace

cur_dir = os.path.dirname(__file__)
_PUSH_SERIALIZED_FIXTURES_PATH = os.path.join(cur_dir, "fixtures", "push_notifications")
_MQTT_RESPONSE_PAYLOADS_SERIALIZED_FIXTURES_PATH = os.path.join(cur_dir, "fixtures", "mqtt_response_payloads")


@pytest.fixture
def uuid_mock() -> str:
    return "11111111111111111111111111111111"


@pytest.fixture
def sub_uuid_mock() -> str:
    return "111111111111"


class CommandExecuteMocker:
    """
    Helper class to patch on the fly the manager's command execute method.
    """
    def __init__(self, manager, method, namespace, data_replacers):
        self.manager = manager
        self.mocked_response = None
        self._old_async_execute_cmd = None
        target = os.path.join(_MQTT_RESPONSE_PAYLOADS_SERIALIZED_FIXTURES_PATH,
                              f"{method.upper()}.{str(namespace.upper())}.json")

        with open(target, "rt") as f:
            text = f.read()
            template_text = string.Template(text)
            self.mocked_response = json.loads(template_text.safe_substitute(data_replacers))
    def __enter__(self):
        self._old_async_execute_cmd = self.manager.async_execute_cmd
        self.manager.async_execute_cmd = MagicMock(return_value=self.mocked_response, spec=MerossManager.async_execute_cmd)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.async_execute_cmd = self._old_async_execute_cmd


@pytest.fixture
def manager_mock():
    manager = MagicMock(spec=MerossManager)

    def _command_mocker(method: str, namespace: str | Namespace, data_replacers: Dict[str, Any]):
        return CommandExecuteMocker(manager, method, namespace, data_replacers)

    manager.mock_execute_command = _command_mocker
    return manager


@pytest.fixture
def push_notification_fixture():
    def get_fixture(push_type: str, data_replacers: Dict[str, Any]) -> Dict[str, Any]:
        target = os.path.join(_PUSH_SERIALIZED_FIXTURES_PATH, f"{push_type}.json")
        data = None
        with open(target, "rt") as f:
            text = f.read()
            template_text = string.Template(text)
            data = json.loads(template_text.safe_substitute(data_replacers))
        return data

    return get_fixture
