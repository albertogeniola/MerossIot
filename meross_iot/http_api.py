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

from meross_iot.model.constants import DEFAULT_MEROSS_HTTP_API
from meross_iot.model.credentials import MerossCloudCreds
# Appears to be used as a part of the signature algorithm as constant "salt" (kinda useless)
from meross_iot.model.http.device import HttpDeviceInfo
from meross_iot.model.http.exception import TooManyTokensException, TokenExpiredException, AuthenticatedPostException, \
    HttpApiError, BadLoginException
from meross_iot.model.http.subdevice import HttpSubdeviceInfo
import os

_LOGGER = logging.getLogger(__name__)

_SECRET = "23x17ahWarFH6w29"
_LOGIN_URL = "%s/v1/Auth/Login"
_LOG_URL = "%s/v1/log/user"
_DEV_LIST = "%s/v1/Device/devList"
_HUB_DUBDEV_LIST = "%s/v1/Hub/getSubDevices"
_LOGOUT_URL = "%s/v1/Profile/logout"


class ErrorCodes(Enum):
    """
    Status codes returned by the Meross HTTP APIs
    """

    CODE_NO_ERROR = 0
    """Not an error"""

    CODE_MISSING_PASSWORD = 1001
    """Wrong or missing password"""

    CODE_UNEXISTING_ACCOUNT = 1002
    """Account does not exist"""

    CODE_DISABLED_OR_DELETED_ACCOUNT = 1003
    """This account has been disabled or deleted"""

    CODE_WRONG_CREDENTIALS = 1004
    """Wrong email or password"""

    CODE_INVALID_EMAIL = 1005
    """Invalid email address"""

    CODE_BAD_PASSWORD_FORMAT = 1006
    """Bad password format"""

    CODE_WRONG_EMAIL = 1008
    """This email is not registered"""

    CODE_TOKEN_INVALID = 1019
    """Token expired"""

    CODE_TOKEN_ERROR = 1022
    """Token error"""

    CODE_TOKEN_EXPIRED = 1200
    """Token has expired"""

    CODE_TOO_MANY_TOKENS = 1301
    """Too many tokens have been issued"""

    CODE_GENERIC_ERROR = 5000
    """Unknown or generic error"""


class MerossHttpClient(object):
    """
    Utility class for dealing with Meross HTTP API.
    This class simplifies the usage of the Meross HTTP API providing login, logout and device listing API.
    """

    def __init__(self,
                 cloud_credentials: MerossCloudCreds,
                 api_base_url: str = DEFAULT_MEROSS_HTTP_API,
                 http_proxy: str = None):
        self._cloud_creds = cloud_credentials
        self.api_url = api_base_url
        self._enable_proxy = False
        self._proxy_type = None
        self._proxy_addr = None
        self._http_proxy = http_proxy

    @property
    def cloud_credentials(self) -> MerossCloudCreds:
        """
        Returns the meross credentials returned by the the HTTP Api
        :return:
        """
        return self._cloud_creds

    @classmethod
    async def async_from_user_password(cls, email: str,
                                       password: str,
                                       api_base_url: str = DEFAULT_MEROSS_HTTP_API,
                                       http_proxy: str = None) -> MerossHttpClient:
        """
        Builds a MerossHttpClient using username/password combination.
        In any case, the login will generate a token, which might expire at any time.

        :param email: Meross account email
        :param password: Meross account password
        :param api_base_url: Meross API base URL
        :param http_proxy: Optional http proxy to use when issuing the requests

        :return: an instance of `MerossHttpClient`
        """
        _LOGGER.debug(f"Logging in with email: {email}, password: XXXXX")
        creds = await cls.async_login(email=email, password=password, api_base_url=api_base_url, http_proxy=http_proxy)
        _LOGGER.debug(f"Login successful!")
        return MerossHttpClient(cloud_credentials=creds, api_base_url=api_base_url)

    @classmethod
    async def async_from_cloud_creds(cls,
                                     creds: MerossCloudCreds,
                                     api_base_url: str = DEFAULT_MEROSS_HTTP_API,
                                     http_proxy: str = None) -> MerossHttpClient:
        # Use _log method to verify the credentials
        verify_creds = await cls._async_log(creds=creds, api_base_url=api_base_url, http_proxy=http_proxy)
        return MerossHttpClient(cloud_credentials=creds, api_base_url=api_base_url, http_proxy=http_proxy)

    @classmethod
    async def async_login(cls,
                          email: str,
                          password: str,
                          creds_env_var_name: str = '__MEROSS_CREDS',
                          api_base_url: str = DEFAULT_MEROSS_HTTP_API,
                          http_proxy: str = None,
                          *args, **kwargs) -> MerossCloudCreds:
        """
        Performs the login against the Meross HTTP endpoint.
        This api returns a MerossCloudCreds object, which contains a token.
        Be cautious when invoking this API: asking for too many tokens as the Meross HTTP API might refuse
        to issue more tokens. Instead, you should keep using the same issued token when possible, possibly
        storing it across sessions. When you are done using a specific token, be sure to invoke logout
        to invalidate it.

        :param email: Meross account email
        :param password: Meross account password
        :param creds_env_var_name: If set, makes thi method store the obtained login-credentials in the specified env variable.
        indicate which env variables stores such credentials
        :param api_base_url: Meross API base url
        :param http_proxy: Optional http proxy to use when to performing the request

        :return: a `MerossCloudCreds` object
        """
        data = {"email": email, "password": password}
        url = _LOGIN_URL % api_base_url
        response_data = await MerossHttpClient._async_authenticated_post(url, params_data=data,

                                                                         mask_params_in_log=True,
                                                                         http_proxy=http_proxy)
        creds = MerossCloudCreds(
            token=response_data["token"],
            key=response_data["key"],
            user_id=response_data["userid"],
            user_email=response_data["email"],
            issued_on=datetime.utcnow()
        )
        if creds_env_var_name is not None:
            os.environ[creds_env_var_name] = base64.b64encode(creds.to_json().encode("utf8")).decode("utf8")
        return creds

    @classmethod
    async def _async_authenticated_post(cls,
                                        url: str,
                                        params_data: dict,
                                        cloud_creds: Optional[MerossCloudCreds] = None,
                                        mask_params_in_log: bool = False,
                                        http_proxy: str = None
                                        ) -> dict:
        nonce = _generate_nonce(16)
        timestamp_millis = int(round(time.time() * 1000))
        encoded_params = _encode_params(params_data)

        # Generate the md5-hash (called signature)
        m = hashlib.md5()
        datatosign = '%s%s%s%s' % (_SECRET, timestamp_millis, nonce, encoded_params)
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
            'params': encoded_params,
            'sign': md5hash,
            'timestamp': timestamp_millis,
            'nonce': nonce
        }

        # Perform the request.
        headers_with_masked_authrorization = headers.copy()
        if 'Authorization' in headers_with_masked_authrorization:
            headers_with_masked_authrorization['Authorization'] = 'XXXX-MASKED-XXXX'

        if not url.lower().startswith("http://") and not url.lower().startswith("https://"):
            _LOGGER.warning("Missing HTTP/HTTPS schema from Base API url. Assuming it's HTTPS://...")
            url = f"https://{url}"

        log_payload = payload
        if mask_params_in_log:
            log_payload = payload.copy()
            log_payload['params'] = 'XXXX-MASKED-XXXX'

        _LOGGER.debug(f"Performing HTTP request against {url}, headers: {headers}, post data: {payload}")
        async with ClientSession() as session:
            async with session.post(url, data=payload, headers=headers, proxy=http_proxy) as response:
                _LOGGER.debug(f"Response Status Code: {response.status}")
                # Check if that is ok.
                if response.status != 200:
                    raise AuthenticatedPostException("Failed request to API. Response code: %s" % str(response.status))

                # Save returned value
                jsondata = await response.json()
                code = jsondata.get('apiStatus')

                error = None
                try:
                    error = ErrorCodes(code)
                except ValueError as e:
                    raise AuthenticatedPostException(f"Unknown/Unhandled response code received from API. "
                                                     f"Response was: {jsondata}")
                finally:
                    if error is None:
                        _LOGGER.error(f"Could not parse error code {code}.")
                    elif error == ErrorCodes.CODE_NO_ERROR:
                        return jsondata.get("data")
                    elif error == ErrorCodes.CODE_TOKEN_EXPIRED:
                        raise TokenExpiredException("The provided token has expired")
                    elif error == ErrorCodes.CODE_TOO_MANY_TOKENS:
                        raise TooManyTokensException("You have issued too many tokens without logging out and your "
                                                     "account might have been temporarly disabled.")
                    elif error in [ErrorCodes.CODE_WRONG_CREDENTIALS, ErrorCodes.CODE_UNEXISTING_ACCOUNT]:
                        raise BadLoginException("Invalid username/Password combination")
                    else:
                        _LOGGER.error(f"Received non-ok API status code: {error.name}. "
                                      f"Failed request to API. Response was: {jsondata}")
                        raise HttpApiError(error)

    async def async_logout(self,
                           *args,
                           **kwargs):
        """
        Invalidates the credentials stored in this object.

        :return: API response data
        """
        _LOGGER.debug(f"Logging out. Invalidating cached credentials {self._cloud_creds}")
        url = _LOGOUT_URL % self.api_url
        result = await MerossHttpClient._async_authenticated_post(url, {},
                                                                  cloud_creds=self._cloud_creds,
                                                                  http_proxy=self._http_proxy)
        self._cloud_creds = None
        _LOGGER.info("Logout succeeded.")
        return result

    async def async_invalidate_credentials(self, creds: MerossCloudCreds):
        """
        Class method used to invalidate credentials without logging in with a full MerossHttpClient.

        :param creds: `MerossCloudCredentials` as returned by `async_login()` or `async_from_user_password()`
        :return: API response data
        """
        url = _LOGOUT_URL % self.api_url
        _LOGGER.debug(f"Logging out. Invalidating cached credentials {creds}")
        result = await MerossHttpClient._async_authenticated_post(url, {}, cloud_creds=creds,
                                                                  http_proxy=self._http_proxy)
        return result

    @classmethod
    async def _async_log(cls,
                         creds: MerossCloudCreds,
                         api_base_url: str = DEFAULT_MEROSS_HTTP_API,
                         http_proxy: str = None,
                         *args,
                         **kwargs) -> dict:
        """
        Executes the LOG HTTP api. So far, it's still unknown whether this is needed and what it does.
        Most probably it logs the device specification to the remote endpoint for stats.

        :return:
        """
        # TODO: talk to the Meross engineer and negotiate a custom system for identifying the API rather than
        #  emulating an Android 6 device.
        data = {'extra': {}, 'model': 'Android,Android SDK built for x86_64', 'system': 'Android',
                'uuid': '493dd9174941ed58waitForOpenWifi', 'vendor': 'Meross', 'version': '6.0'}
        url = _LOG_URL % api_base_url
        return await cls._async_authenticated_post(url, params_data=data, cloud_creds=creds, http_proxy=http_proxy)

    async def async_list_devices(self,
                                 *args,
                                 **kwargs) -> List[HttpDeviceInfo]:
        """
        Asks to the HTTP api to list the Meross device belonging to the given user account.

        :return: a list of `HttpDeviceInfo`
        """
        url = _DEV_LIST % self.api_url
        result = await MerossHttpClient._async_authenticated_post(url, {}, cloud_creds=self._cloud_creds, http_proxy=self._http_proxy)
        return [HttpDeviceInfo.from_dict(x) for x in result]

    async def async_list_hub_subdevices(self,
                                        hub_id: str,
                                        *args,
                                        **kwargs) -> List[HttpSubdeviceInfo]:
        """
        Returns the sub-devices associated to the given hub.

        :param hub_id: Meross native UUID of the HUB

        :return: a list of `HttpSubdeviceInfo`
        """
        url = _HUB_DUBDEV_LIST % self.api_url
        result = await MerossHttpClient._async_authenticated_post(url, {"uuid": hub_id}, cloud_creds=self._cloud_creds, http_proxy=self._http_proxy)
        return [HttpSubdeviceInfo.from_dict(x) for x in result]

    def set_http_proxy(self, proxy_url: str):
        # TODO: validate proxy schema
        self._http_proxy = proxy_url


def _encode_params(parameters: dict):
    jsonstring = json.dumps(parameters)
    return str(base64.b64encode(jsonstring.encode("utf8")), "utf8")


def _generate_nonce(length: int):
    return ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(length))


def unauthenticated_command_executor(func, *args, **kwargs):
    def cmd(*iargs, **ikwargs):
        import asyncio

        # Fix event loop for Windows env
        if os.name == 'nt':
            import asyncio
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

        params = {k: v for (k, v) in iargs[0].__dict__.items() if k not in ("func",)}

        loop = asyncio.get_event_loop()
        data = loop.run_until_complete(func(**params))
        print(data)
        loop.close()

    return cmd


def authenticated_command_executor(method, *args, **kwargs):
    def cmd(*iargs, **ikwargs):
        import asyncio
        import os

        async def execute(method, *args, **kwargs):
            b64creds = os.getenv("__MEROSS_CREDS", None)
            if b64creds is None:
                raise ValueError("This method requires __MEROSS_CREDS env variable set. "
                                 "Please invoke auth login first.")

            jsoncreds = base64.b64decode(b64creds)
            creds = MerossCloudCreds.from_json(jsoncreds)
            client = await MerossHttpClient.async_from_cloud_creds(creds)
            m = getattr(client, method)
            return await m(*args, **kwargs)

        # Fix event loop for Windows env
        if os.name == 'nt':
            import asyncio
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

        params = {k: v for (k, v) in iargs[0].__dict__.items() if k not in ("func", "credentials")}

        loop = asyncio.get_event_loop()
        data = loop.run_until_complete(execute(method, **params))
        print(data)
        loop.close()

    return cmd


def main():
    import sys
    from argparse import ArgumentParser
    # Root parser
    parser = ArgumentParser(
        prog="meross_api_cli",
        description="Meross HTTP API utility",
        epilog="Created by Alberto Geniola")
    subparsers = parser.add_subparsers()

    # auth parser
    parser_auth = subparsers.add_parser('auth')
    auth_subparsers = parser_auth.add_subparsers()

    # auth login
    auth_login = auth_subparsers.add_parser('login',
                                            description="Logs in into meross HTTP api and prints out the credentials")
    auth_login.add_argument('--email', type=str, required=True, help='Account username/email')
    auth_login.add_argument('--password', type=str, required=True, help='Account password')
    auth_login.add_argument('--set-env-var', default=True, action='store_true',
                            help='When set, stores the credentials into the environment var MEROSS_CREDS')
    auth_login.set_defaults(func=unauthenticated_command_executor(MerossHttpClient.async_login))

    # auth logout
    auth_login = auth_subparsers.add_parser('logout', description="Logs out by invalidating the current token")
    auth_login.set_defaults(func=authenticated_command_executor("async_logout"))

    # device parser
    parser_device = subparsers.add_parser('device')
    device_subparsers = parser_device.add_subparsers()

    # devlist
    dev_list = device_subparsers.add_parser('list', description="Lists meross devices")
    dev_list.set_defaults(func=authenticated_command_executor("async_list_devices"))

    # hub parser
    parser_hub = subparsers.add_parser('hub')
    parser_hub.add_argument("--hub_id", required=True, help="Hub uuid")
    hub_subparsers = parser_hub.add_subparsers()

    # getsubdevices
    subdev_list = hub_subparsers.add_parser('list_sub_devices', description="Lists subdevices for the given hub")
    subdev_list.set_defaults(func=authenticated_command_executor("async_list_hub_subdevices"))

    data = parser.parse_args(sys.argv[1:])
    data.func(data)


if __name__ == '__main__':
    main()
