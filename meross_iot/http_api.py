from __future__ import annotations  # Needed for returning the same class type where using factory static builders

import base64
import hashlib
import json
import logging
import random
import string
import time
from datetime import datetime
from enum import Enum
from typing import Optional, List

from aiohttp import ClientSession

from meross_iot.model.credentials import MerossCloudCreds
# Appears to be used as a part of the signature algorithm as constant "salt" (kinda useless)
from meross_iot.model.http.device import HttpDeviceInfo
from meross_iot.model.http.exception import TooManyTokensException, TokenExpiredException, AuthenticatedPostException
from meross_iot.model.http.subdevice import HttpSubdeviceInfo

_LOGGER = logging.getLogger(__name__)


_SECRET = "23x17ahWarFH6w29"
_MEROSS_URL = "https://iot.meross.com"
_LOGIN_URL = f"{_MEROSS_URL}/v1/Auth/Login"
_LOG_URL = f"{_MEROSS_URL}/v1/log/user"
_DEV_LIST = f"{_MEROSS_URL}/v1/Device/devList"
_HUB_DUBDEV_LIST = f"{_MEROSS_URL}/v1/Hub/getSubDevices"
_LOGOUT_URL = f"{_MEROSS_URL}/v1/Profile/logout"


class ErrorCodes(Enum):

    CODE_NO_ERROR = 0
    """Not an error"""

    CODE_TOKEN_INVALID = 1019
    """Token expired"""

    CODE_TOKEN_EXPIRED = 1022
    """Token has expired"""

    CODE_TOO_MANY_TOKENS = 1301
    """Too many tokens have been issued"""


class MerossHttpClient(object):
    """
    Utility class for dealing with Meross HTTP API.
    This class simplifies the usage of the Meross HTTP API providing login, logout and device listing API.
    """

    def __init__(self, cloud_credentials: MerossCloudCreds):
        self._cloud_creds = cloud_credentials

    @property
    def cloud_credentials(self) -> MerossCloudCreds:
        """
        Returns the meross credentials returned by the the HTTP Api
        :return:
        """
        return self._cloud_creds

    @classmethod
    async def async_from_user_password(cls, email: str, password: str) -> MerossHttpClient:
        """
        Builds a MerossHttpClient using username/password combination.
        In any case, the login will generate a token, which might expire at any time.

        :param email: Meross account email
        :param password: Meross account password

        :return:
        """
        _LOGGER.debug(f"Logging in with email: {email}, password: XXXXX")
        creds = await cls.async_login(email, password)
        _LOGGER.debug(f"Login successful!")
        return MerossHttpClient(cloud_credentials=creds)

    @classmethod
    async def async_login(cls, email: str, password: str) -> MerossCloudCreds:
        """
        Performs the login against the Meross HTTP endpoint.
        This api returns a MerossCloudCreds object, which contains a token.
        Be cautious when invoking this API: asking for too many tokens as the Meross HTTP API might refuse
        to issue more tokens. Instead, you should keep using the same issued token when possible, possibly
        storing it across sessions. When you are done using a specific token, be sure to invoke logout
        to invalidate it.

        :param email: Meross account email
        :param password: Meross account password

        :return:
        """
        data = {"email": email, "password": password}
        response_data = await cls._async_authenticated_post(_LOGIN_URL, params_data=data)
        creds = MerossCloudCreds(
            token=response_data["token"],
            key=response_data["key"],
            user_id=response_data["userid"],
            user_email=response_data["email"],
            issued_on=datetime.utcnow()
        )
        return creds

    @classmethod
    async def _async_authenticated_post(cls,
                                        url: str,
                                        params_data: dict,
                                        cloud_creds: Optional[MerossCloudCreds] = None
                                        ) -> dict:

        nonce = _generate_nonce(16)
        timestamp_millis = int(round(time.time() * 1000))
        login_params = _encode_params(params_data)

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
        _LOGGER.debug(f"Performing HTTP request against {url}, headers: {headers}, post data: {payload}")
        async with ClientSession() as session:
            async with session.post(url, data=payload, headers=headers) as response:
                _LOGGER.debug(f"Response Status Code: {response.status}")
                # Check if that is ok.
                if response.status != 200:
                    raise AuthenticatedPostException("Failed request to API. Response code: %d" % str(response.status))

                # Save returned value
                jsondata = await response.json()
                code = jsondata.get('apiStatus')

                error = None
                try:
                    error = ErrorCodes(code)
                except ValueError as e:
                    raise AuthenticatedPostException(f"Unknown/Unhandled response code received from API. "
                                                     f"Response was: {jsondata}")

                if error == ErrorCodes.CODE_NO_ERROR:
                    return jsondata.get("data")
                elif error == ErrorCodes.CODE_TOKEN_EXPIRED:
                    raise TokenExpiredException("The provided token has expired")
                elif error == ErrorCodes.CODE_TOO_MANY_TOKENS:
                    raise TooManyTokensException("You have issued too many tokens without logging out.")
                else:
                    raise AuthenticatedPostException(f"Failed request to API. Response was: {jsondata}")

    async def async_logout(self):
        """
        Invalidates the credentials stored in this object.

        :return:
        """
        _LOGGER.debug(f"Logging out. Invalidating cached credentials {self._cloud_creds}")
        result = await self._async_authenticated_post(_LOGOUT_URL, {}, cloud_creds=self._cloud_creds)
        self._cloud_creds = None
        _LOGGER.info("Logout succeeded.")
        return result

    @classmethod
    async def async_invalidate_credentials(cls, creds: MerossCloudCreds):
        """
        Class method used to invalidate credentials without logging in with a full MerossHttpClient.

        :param creds: `MerossCloudCredentials` as returned by `async_login()` or `async_from_user_password()`
        :return:
        """
        _LOGGER.debug(f"Logging out. Invalidating cached credentials {creds}")
        result = await cls._async_authenticated_post(_LOGOUT_URL, {}, cloud_creds=creds)
        return result

    async def _async_log(self) -> dict:
        """
        Executes the LOG HTTP api. So far, it's still unknown whether this is needed and what it does.
        Most probably it logs the device specification to the remote endpoint for stats.

        :return:
        """
        # TODO: talk to the Meross engineer and negotiate a custom system for identifying the API rather than
        #  emulating an Android 6 device.
        data = {'extra': {}, 'model': 'Android,Android SDK built for x86_64', 'system': 'Android',
                'uuid': '493dd9174941ed58waitForOpenWifi', 'vendor': 'Meross', 'version': '6.0'}
        return await self._async_authenticated_post(_LOG_URL, params_data=data)

    async def async_list_devices(self) -> List[HttpDeviceInfo]:
        """
        Asks to the HTTP api to list the Meross device belonging to the given user account.

        :return:
        """
        result = await self._async_authenticated_post(_DEV_LIST, {}, cloud_creds=self._cloud_creds)
        return [HttpDeviceInfo.from_dict(x) for x in result]

    async def async_list_hub_subdevices(self, hub_id: str) -> List[HttpSubdeviceInfo]:
        """
        Returns the sub-devices associated to the given hub.

        :param hub_id: Meross native UUID of the HUB

        :return:
        """
        result = await self._async_authenticated_post(_HUB_DUBDEV_LIST, {"uuid": hub_id}, cloud_creds=self._cloud_creds)
        return [HttpSubdeviceInfo.from_dict(x) for x in result]


def _encode_params(parameters: dict):
    jsonstring = json.dumps(parameters)
    return str(base64.b64encode(jsonstring.encode("utf8")), "utf8")


def _generate_nonce(length: int):
    return ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(length))

