import re
import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, Union
from meross_iot.cloud.device import AbstractMerossDevice


_LOGGER = logging.getLogger(__name__)


camel_pat = re.compile(r'([A-Z])')
under_pat = re.compile(r'_([a-z])')


def _camel_to_underscore(key):
    return camel_pat.sub(lambda x: '_' + x.group(1).lower(), key)


def _underscore_to_camel(key):
    return under_pat.sub(lambda x: x.group(1).upper(), key)


class GenericPushNotification(object):
    """Represents a generic push notification received from the Meross cloud"""
    def __init__(self,
                 namespace: str,
                 raw_data: Optional[dict] = None):
        self.namespace = namespace
        self._raw_data = raw_data


class DevicePushNotification(GenericPushNotification):
    """Represents a push notification regarding a specific device from the Meross cloud"""
    def __init__(self,
                 namespace: str,
                 raw_data: Optional[dict] = None,
                 device: AbstractMerossDevice = None
                 ):
        super().__init__(namespace=namespace, raw_data=raw_data)
        self.device = device


class AbstractPayload(ABC):
    @classmethod
    @abstractmethod
    def from_dict(cls, json_dict: dict):
        pass

    def to_dict(self) -> dict:
        pass


class BaseDictPayload(AbstractPayload):
    @classmethod
    def from_dict(cls, json_dict: dict):
        obj = cls()
        for key in json_dict:
            attr_name = _camel_to_underscore(key)
            if hasattr(obj, attr_name):
                setattr(obj, attr_name, json_dict[key])
            else:
                _LOGGER.warning(f"The dict object offered a key ({key}) that is not available "
                                f"in the current object (no {attr_name} was found)")
        return obj

    def to_dict(self) -> dict:
        res = {}
        for k, v in vars(self).items():
            new_key = _underscore_to_camel(k)
            res[new_key] = v
        return res
