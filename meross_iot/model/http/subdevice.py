import json
import logging

from meross_iot.model.shared import BaseDictPayload

_LOGGER = logging.getLogger(__name__)


class HttpSubdeviceInfo(BaseDictPayload):
    def __init__(self,
                 sub_device_id: str,
                 sub_device_type: str,
                 sub_device_name: str,
                 sub_device_icon_id: str,
                 *args, **kwargs):

        super().__init__(*args, **kwargs)
        self.sub_device_id = sub_device_id
        self.sub_device_type = sub_device_type
        self.sub_device_name = sub_device_name
        self.sub_device_icon_id = sub_device_icon_id

        # Keep this for backwards compatibility. As per issue #428
        # it seems these attributes are no longer provided by the HTTP API
        self.true_id = kwargs.get("true_id")
        self.sub_device_vendor = kwargs.get("sub_device_vendor")

    def __repr__(self):
        return json.dumps(self.__dict__)

    def __str__(self):
        basic_info = f"{self.sub_device_name} ({self.sub_device_type}, ID {self.sub_device_id})"
        return basic_info
