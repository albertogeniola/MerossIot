import json
import os
from datetime import datetime

from meross_iot.cloud.exceptions.CredentialsException import InvalidStoredCredentialsException


class MerossCloudCreds(object):
    def __init__(self, token, key, user_id, user_email, issued_on):
        self.token = token
        self.key = key
        self.user_id = user_id
        self.user_email = user_email
        self.issued_on = issued_on

    def serialize_key_token(self, filepath):
        d = {
            'token': self.token,
            'key': self.key,
            'user_id': self.user_id,
            'user_email': self.user_email,
            'issued_on': self.issued_on.isoformat()
        }

        with open(file=filepath, mode="wb+") as f:
            json.dump(d, f)

    @staticmethod
    def load_from_json_file(filepath):
        if not os.path.isfile(filepath):
            raise InvalidStoredCredentialsException("Invalid file path: %s" % filepath)

        with open(file=filepath, mode="rb") as f:
            data = json.load(f)
            token = data.get('token')
            key = data.get('key')
            user_id = data.get('user_id')
            user_email = data.get('user_email')
            issued_on = data.get('issued_on')

            if token is None:
                raise InvalidStoredCredentialsException("The stored credentials are not valid. Missing token attribute.")
            if key is None:
                raise InvalidStoredCredentialsException("The stored credentials are not valid. Missing key attribute.")
            if user_id is None:
                raise InvalidStoredCredentialsException("The stored credentials are not valid. Missing user_id attribute.")
            if user_email is None:
                raise InvalidStoredCredentialsException("The stored credentials are not valid. Missing user_email attribute.")
            if issued_on is None:
                raise InvalidStoredCredentialsException("The stored credentials are not valid. Missing issued_on attribute.")
            else:
                issued_on = datetime.fromisoformat(issued_on)

            return MerossCloudCreds(token=token, key=key, user_id=user_id, user_email=user_email, issued_on=issued_on)
