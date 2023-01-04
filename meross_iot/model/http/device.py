import json
import logging
from datetime import datetime
from typing import Union, List

from meross_iot.model.constants import DEFAULT_MQTT_PORT, DEFAULT_MQTT_HOST
from meross_iot.model.enums import OnlineStatus
from meross_iot.model.shared import BaseDictPayload
from meross_iot.utilities.network import extract_domain, extract_port

_LOGGER = logging.getLogger(__name__)


class HttpDeviceInfo(BaseDictPayload):
    def __init__(self,
                 uuid: str,
                 online_status: Union[int, OnlineStatus],
                 dev_name: str,
                 device_type: str,
                 channels: List[dict],
                 fmware_version: str,
                 hdware_version: str,
                 domain: str,
                 reserved_domain: str,
                 sub_type: str = None,
                 bind_time: Union[int, datetime] = None,
                 skill_number: str = None,
                 user_dev_icon: str = None,
                 icon_type: int = None,
                 region: str = None,
                 dev_icon_id: str = None,
                 *args, **kwargs):

        super().__init__(*args, **kwargs)
        self.uuid = uuid
        if isinstance(online_status, int):
            self.online_status = OnlineStatus(online_status)
        elif isinstance(online_status, OnlineStatus):
            self.online_status = online_status
        else:
            _LOGGER.warning(f"Provided online_status is not int neither OnlineStatus. It will be ignored.")
            self.online_status = None

        self.dev_name = dev_name
        self.dev_icon_id = dev_icon_id
        if isinstance(bind_time, int):
            self.bind_time = datetime.utcfromtimestamp(bind_time)
        elif isinstance(bind_time, datetime):
            self.bind_time = bind_time
        elif isinstance(bind_time, str):
            self.bind_time = datetime.strptime(bind_time, "%Y-%m-%dT%H:%M:%S")
        else:
            _LOGGER.warning(f"Provided bind_time is not int neither datetime. It will be ignored.")
            self.bind_time = None

        self.device_type = device_type
        self.sub_type = sub_type
        self.channels = channels
        self.region = region
        self.fmware_version = fmware_version
        self.hdware_version = hdware_version
        self.user_dev_icon = user_dev_icon
        self.icon_type = icon_type
        self.skill_number = skill_number
        self.domain = domain
        self.reserved_domain = reserved_domain

    def get_mqtt_host(self) -> str:
        """Infers the mqtt server host for this device"""
        # Prefer domain over reserved domain
        if self.domain is not None:
            return extract_domain(self.domain)
        if self.reserved_domain is not None:
            return extract_domain(self.reserved_domain)
        _LOGGER.warning("Could not find domain info for device %s, returning default domain %s", str(self.uuid), DEFAULT_MQTT_HOST)
        return DEFAULT_MQTT_HOST

    def get_mqtt_port(self) -> int:
        """Infers the mqtt server port for this device"""
        # Prefer domain over reserved domain
        if self.domain is not None:
            return extract_port(self.domain, DEFAULT_MQTT_PORT)
        if self.reserved_domain is not None:
            return extract_port(self.reserved_domain, DEFAULT_MQTT_PORT)
        _LOGGER.warning("Could not find domain info for device %s, returning default port %d", str(self.uuid),
                    DEFAULT_MQTT_PORT)
        return DEFAULT_MQTT_PORT

    def __repr__(self):
        return json.dumps(self.__dict__, default=lambda x: x.isoformat() if isinstance(x,datetime) else x.name if(isinstance(x,OnlineStatus)) else "NOT-SERIALIZABLE")

    def __str__(self):
        basic_info = f"{self.dev_name} ({self.device_type}, HW {self.hdware_version}, FW {self.fmware_version})"
        return basic_info