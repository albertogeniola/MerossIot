import base64
import hashlib
import json
import random
import string
import time

import requests

from meross_iot.device_factory import build_wrapper

# Appears to be used as a part of the signature algorithm as constant "salt" (kinda useless)
_SECRET = "23x17ahWarFH6w29"
_MEROSS_URL = "https://iot.meross.com"
_LOGIN_URL = "%s%s" % (_MEROSS_URL, "/v1/Auth/Login")
_LOG_URL = "%s%s" % (_MEROSS_URL, "/v1/log/user")
_DEV_LIST = "%s%s" % (_MEROSS_URL, "/v1/Device/devList")


class MerossHttpClient:
    _token = None
    _key = None
    _userid = None
    _userEmail = None

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
            "Authorization": "Basic" if self._token is None else "Basic %s" % self._token,
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
            raise AuthenticatedPostException()

        # Save returned value
        jsondata = r.json()
        # print(jsondata)

        if jsondata["info"].lower() != "success":
            raise AuthenticatedPostException()

        return jsondata["data"]

    def _encode_params(self,
                       parameters  # type: dict
                       ):
        jsonstring = json.dumps(parameters)
        return str(base64.b64encode(jsonstring.encode("utf8")), "utf8")

    def _generate_nonce(self, length):
        return ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(length))

    def _login(self):
        try:
            data = {"email": self._email, "password": self._password}
            response_data = self._authenticated_post(_LOGIN_URL, params_data=data)
            self._token = response_data["token"]
            self._key = response_data["key"]
            self._userid = response_data["userid"]
            self._userEmail = response_data["email"]
            self._authenticated = True
        except:
            return False

        try:
            # The protocol does not really need the following call. However we want to be nice do it anyways
            self._log()
        except:
            pass

        return True

    def _log(self, ):
        data = {'extra': {}, 'model': 'Android,Android SDK built for x86_64', 'system': 'Android',
                'uuid': '493dd9174941ed58waitForOpenWifi', 'vendor': 'Meross', 'version': '6.0'}
        response_data = self._authenticated_post(_LOG_URL, params_data=data)

    def list_devices(self):
        if not self._authenticated and not self._login():
            raise UnauthorizedException()

        return self._authenticated_post(_DEV_LIST, {})

    def list_supported_devices(self, online_only=True):
        supported_devices = []
        for dev in self.list_devices():
            deviceType = dev['deviceType']
            online = dev['onlineStatus']

            if online_only and online != 1:
                # The device is not online, so we skip it.
                continue

            device = build_wrapper(self._token, self._key, self._userid, deviceType, dev)
            if device is not None:
                supported_devices.append(device)
            # else log...

        return supported_devices


class AuthenticatedPostException(Exception):
    pass


class UnauthorizedException(Exception):
    pass
