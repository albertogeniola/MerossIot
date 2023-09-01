import json
from datetime import datetime
from typing import Union


class MerossCloudCreds(object):
    """
    Utility class that holds Meross Cloud credentials for a given user.
    """
    def __init__(self, token: str, key: str, user_id: str, user_email: str, issued_on: Union[datetime, str], domain: str, mqtt_domain :str, mfa_lock_expire:int):
        self.token = token
        self.key = key
        self.user_id = user_id
        self.user_email = user_email
        self.domain = domain
        self.mqtt_domain = mqtt_domain,
        self.mfa_lock_expire = mfa_lock_expire

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
            "mfa_lock_expire": self.mfa_lock_expire,
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
        return MerossCloudCreds(**data)

    def __repr__(self):
        return self.to_json()
