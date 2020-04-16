import base64
import hashlib
import json
import random
import string
import time
from enum import Enum

import requests

from meross_iot.cloud.exceptions.TokenExpiredException import TokenExpiredException
from meross_iot.cloud.exceptions.TooManyTokensException import TooManyTokensException
from meross_iot.credentials import MerossCloudCreds
from meross_iot.logger import API_LOGGER as l
from datetime import datetime


# Appears to be used as a part of the signature algorithm as constant "salt" (kinda useless)
_SECRET = "23x17ahWarFH6w29"
_MEROSS_URL = "https://iot.meross.com"
_LOGIN_URL = "%s%s" % (_MEROSS_URL, "/v1/Auth/Login")
_LOG_URL = "%s%s" % (_MEROSS_URL, "/v1/log/user")
_DEV_LIST = "%s%s" % (_MEROSS_URL, "/v1/Device/devList")
_HUB_DUBDEV_LIST = "%s%s" % (_MEROSS_URL, "/v1/Hub/getSubDevices")
_LOGOUT_URL = "%s%s" % (_MEROSS_URL, "/v1/Profile/logout")


class ErrorCodes(Enum):
    CODE_NO_ERROR = 0
    CODE_TOKEN_EXPIRED = 1019
    CODE_TOO_MANY_TOKENS = 1301


# TODO: implement Token check API call (if any)
#       and automatic token renewal
class MerossHttpClient:
    def __init__(self, cloud_credentials):
        self._cloud_creds = cloud_credentials

    @classmethod
    def from_user_password(cls, email, password):
        creds = cls.login(email, password)
        return MerossHttpClient(cloud_credentials=creds)

    @classmethod
    def login(cls, email, password):
        data = {"email": email, "password": password}
        response_data = cls._authenticated_post(_LOGIN_URL, params_data=data)
        creds = MerossCloudCreds(
            token=response_data["token"],
            key=response_data["key"],
            user_id=response_data["userid"],
            user_email=response_data["email"],
            issued_on=datetime.utcnow()
        )
        return creds

    @classmethod
    def _authenticated_post(cls,
                            url,  # type: str
                            params_data,  # type: dict,
                            cloud_creds=None
                            ):

        nonce = cls._generate_nonce(16)
        timestamp_millis = int(round(time.time() * 1000))
        login_params = cls._encode_params(params_data)

        # Generate the md5-hash (called signature)
        m = hashlib.md5()
        datatosign = '%s%s%s%s' % (_SECRET, timestamp_millis, nonce, login_params)
        m.update(datatosign.encode("utf8"))
        md5hash = m.hexdigest()

        headers = {
            "Authorization": "Basic" if cloud_creds is None else "Basic %s" % cloud_creds.token,
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
        code = jsondata.get('apiStatus')

        if jsondata["info"].lower() != "success":
            l.warn("Failed request to API. Response was: %s" % str(jsondata))
            raise AuthenticatedPostException("Failed request to API. Response was: %s" % str(jsondata))

        try:
            result_code = ErrorCodes(code)
            if result_code == ErrorCodes.CODE_NO_ERROR:
                return jsondata["data"]
            elif result_code == ErrorCodes.CODE_TOKEN_EXPIRED:
                raise TokenExpiredException("The provided token has expired")
            elif result_code == ErrorCodes.CODE_TOO_MANY_TOKENS:
                raise TooManyTokensException("You have issued too many tokens without logging out.")
            else:
                raise AuthenticatedPostException("Failed request to API. Response was: %s" % str(jsondata))
        except:
            raise AuthenticatedPostException("Cannot parse response code. Response was: %s" % str(jsondata))

    @classmethod
    def _encode_params(cls,
                       parameters  # type: dict
                       ):
        jsonstring = json.dumps(parameters)
        return str(base64.b64encode(jsonstring.encode("utf8")), "utf8")

    @classmethod
    def _generate_nonce(cls, length):
        return ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(length))

    def _log(self):
        data = {'extra': {}, 'model': 'Android,Android SDK built for x86_64', 'system': 'Android',
                'uuid': '493dd9174941ed58waitForOpenWifi', 'vendor': 'Meross', 'version': '6.0'}
        self._authenticated_post(_LOG_URL, params_data=data)

    def list_devices(self):
        return self._authenticated_post(_DEV_LIST, {}, cloud_creds=self._cloud_creds)

    def get_cloud_credentials(self):
        return self._cloud_creds

    def list_hub_subdevices(self, hub_id):
        return self._authenticated_post(_HUB_DUBDEV_LIST, {"uuid": hub_id}, cloud_creds=self._cloud_creds)

    def logout(self):
        return self._authenticated_post(_LOGOUT_URL, {}, cloud_creds=self._cloud_creds)


class AuthenticatedPostException(Exception):
    pass


class UnauthorizedException(Exception):
    pass
