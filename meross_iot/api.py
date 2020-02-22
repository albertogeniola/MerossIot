import base64
import hashlib
import json
import random
import string
import time

import requests

from meross_iot.credentials import MerossCloudCreds
from meross_iot.logger import API_LOGGER as l

# Appears to be used as a part of the signature algorithm as constant "salt" (kinda useless)
_SECRET = "23x17ahWarFH6w29"
_MEROSS_URL = "https://iot.meross.com"
_LOGIN_URL = "%s%s" % (_MEROSS_URL, "/v1/Auth/Login")
_LOG_URL = "%s%s" % (_MEROSS_URL, "/v1/log/user")
_DEV_LIST = "%s%s" % (_MEROSS_URL, "/v1/Device/devList")
_HUB_DUBDEV_LIST = "%s%s" % (_MEROSS_URL, "/v1/Hub/getSubDevices")


class MerossHttpClient:
    _cloud_creds = None

    _email = None
    _password = None
    _authenticated = False

    def __init__(self, email, password):
        self._email = email
        self._password = password

    def _authenticated_post(self,
                            url,  # type: str
                            params_data  # type: dict
                            ):

        nonce = self._generate_nonce(16)
        timestamp_millis = int(round(time.time() * 1000))
        login_params = self._encode_params(params_data)

        # Generate the md5-hash (called signature)
        m = hashlib.md5()
        datatosign = '%s%s%s%s' % (_SECRET, timestamp_millis, nonce, login_params)
        m.update(datatosign.encode("utf8"))
        md5hash = m.hexdigest()

        headers = {
            "Authorization": "Basic" if self._cloud_creds is None else "Basic %s" % self._cloud_creds.token,
            "vender": "Meross",
            "AppVersion": "1.3.0",
            "AppLanguage": "EN",
            "User-Agent": "okhttp/3.6.0"
        }

        payload = {
            'params': login_params,
            'sign': md5hash,
            'timestamp': timestamp_millis,
            'nonce': nonce
        }

        # Perform the request.
        r = requests.post(url, data=payload, headers=headers)

        # Check if that is ok.
        if r.status_code != 200:
            raise AuthenticatedPostException("Failed request to API. Response code: %d" % str(r.status_code))

        # Save returned value
        jsondata = r.json()

        if jsondata["info"].lower() != "success":
            l.warn("Failed request to API. Response was: %s" % str(jsondata))
            raise AuthenticatedPostException("Failed request to API. Response was: %s" % str(jsondata))

        return jsondata["data"]

    @staticmethod
    def _encode_params(parameters  # type: dict
                       ):
        jsonstring = json.dumps(parameters)
        return str(base64.b64encode(jsonstring.encode("utf8")), "utf8")

    @staticmethod
    def _generate_nonce(length):
        return ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(length))

    def _login(self):
        try:
            data = {"email": self._email, "password": self._password}
            response_data = self._authenticated_post(_LOGIN_URL, params_data=data)
            creds = MerossCloudCreds()
            creds.token = response_data["token"]
            creds.key = response_data["key"]
            creds.user_id = response_data["userid"]
            creds.user_email = response_data["email"]
            self._cloud_creds = creds
            self._authenticated = True
        except:
            l.exception("Error occurred when logging in.")
            return False

        try:
            # The protocol does not really need the following call. However we want to be nice do it anyways
            self._log()
        except:
            l.exception("Error occurred when logging in.")
            pass

        return True

    def _log(self):
        data = {'extra': {}, 'model': 'Android,Android SDK built for x86_64', 'system': 'Android',
                'uuid': '493dd9174941ed58waitForOpenWifi', 'vendor': 'Meross', 'version': '6.0'}
        self._authenticated_post(_LOG_URL, params_data=data)

    def list_devices(self):
        if not self._authenticated and not self._login():
            raise UnauthorizedException()

        return self._authenticated_post(_DEV_LIST, {})

    def get_cloud_credentials(self):
        if not self._authenticated and not self._login():
            raise UnauthorizedException()

        return self._cloud_creds

    def list_hub_subdevices(self, hub_id):
        if not self._authenticated and not self._login():
            raise UnauthorizedException()

        return self._authenticated_post(_HUB_DUBDEV_LIST, {"uuid": hub_id})


class AuthenticatedPostException(Exception):
    pass


class UnauthorizedException(Exception):
    pass
