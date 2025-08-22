import json
from datetime import datetime
from typing import Union

from meross_iot.model.constants import DEFAULT_MQTT_HOST


class MerossCloudCreds(object):
    """
    Utility class that holds Meross Cloud credentials for a given user.
    """
    def __init__(self, token: str, key: str, user_id: str, user_email: str, issued_on: Union[datetime, str], domain: str, mqtt_domain :str):
        self.token = token
        self.key = key
        self.user_id = user_id
        self.user_email = user_email
        self.domain = domain
        self.mqtt_domain = mqtt_domain

        if isinstance(issued_on, datetime):
            self.issued_on = issued_on
        else:
            self.issued_on = datetime.fromisoformat(issued_on)

    def to_json(self) -> str:
        """
        Serializes the current object to a json string
        :return:
        """
        return json.dumps({
            "token": self.token,
            "key": self.key,
            "user_id": self.user_id,
            "user_email": self.user_email,
            "domain": self.domain,
            "mqtt_domain": self.mqtt_domain,
            "issued_on": self.issued_on.isoformat()
        })

    @classmethod
    def from_json(cls, json_string: str):
        """
        Builds a MerossCloudCreds instance from a previously serialized json string
        :param json_string:
        :return:
        """
        data = json.loads(json_string)
        # The old version of this object did not store the domain and mqttDomain.
        # We add in here the logic we need to ensure backward compatibility.
        if 'mqtt_domain' not in data:
            data['mqtt_domain'] = DEFAULT_MQTT_HOST
        if 'domain' not in data:
            data['domain'] = "http://iot.meross.com"
        res = MerossCloudCreds(**data)
        return res

    def __repr__(self):
        return self.to_json()
