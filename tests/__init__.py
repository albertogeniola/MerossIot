import base64
import logging
import os
import sys
from typing import Tuple

from meross_iot.http_api import MerossHttpClient
from meross_iot.model.credentials import MerossCloudCreds

_TEST_API_BASE_URL = os.environ.get('MEROSS_API_URL', "https://iotx-us.meross.com")
_TEST_EMAIL = os.environ.get('MEROSS_EMAIL')
_TEST_EMAIL_MFA = os.environ.get('MEROSS_EMAIL_MFA')
_TEST_PASSWORD = os.environ.get('MEROSS_PASSWORD')
_TEST_CREDS = os.getenv("__MEROSS_CREDS")


_LOGGER = logging.getLogger(__name__)
logging.basicConfig(
    format="%(levelname)s:%(message)s", level=logging.DEBUG, stream=sys.stdout
)


async def async_get_client() -> Tuple[MerossHttpClient, bool]:
    opt_params = {}
    if _TEST_API_BASE_URL is not None:
        api_base_url = _TEST_API_BASE_URL
    else:
        api_base_url = "https://iotx-us.meross.com"

    if _TEST_CREDS is not None:
        _LOGGER.info("Found cached credentials. Using them.")
        jsoncreds = str(base64.b64decode(_TEST_CREDS), 'utf8')
        creds = MerossCloudCreds.from_json(jsoncreds)
        return await MerossHttpClient.async_from_cloud_creds(creds, **opt_params), False
    else:
        _LOGGER.info("Using username-password credentials")
        return await MerossHttpClient.async_from_user_password(api_base_url=api_base_url, email=_TEST_EMAIL, password=_TEST_PASSWORD, **opt_params), True
