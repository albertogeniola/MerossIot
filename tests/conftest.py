import string
import json
from typing import Dict, Any, Tuple
from unittest.mock import MagicMock

import pytest
import os

from meross_iot.manager import MerossManager
from meross_iot.model.enums import Namespace
from meross_iot.model.http.device import HttpDeviceInfo

_PUSH_SERIALIZED_FIXTURES_PATH = os.path.join("fixtures","push_notifications")


@pytest.fixture
def uuid_mock() -> str:
    return "25051373484278620801c4e7ae1742ad"


@pytest.fixture
def sub_uuid_mock() -> str:
    return "151011100BE9"


@pytest.fixture
def manager_mock():
    manager = MerossManager(http_client=MagicMock())
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
