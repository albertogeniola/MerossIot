import base64
import logging
import os
import sys
from typing import Tuple

from meross_iot.http_api import MerossHttpClient
from meross_iot.model.credentials import MerossCloudCreds

API_BASE_URL = os.environ.get('MEROSS_API_URL')
EMAIL = os.environ.get('MEROSS_EMAIL')
PASSWORD = os.environ.get('MEROSS_PASSWORD')
CREDS = os.getenv("__MEROSS_CREDS")


_LOGGER = logging.getLogger(__name__)
logging.basicConfig(
    format="%(levelname)s:%(message)s", level=logging.DEBUG, stream=sys.stdout
)


async def async_get_client() -> Tuple[MerossHttpClient, bool]:
    opt_params = {}
    if API_BASE_URL is not None:
        opt_params['api_base_url'] = API_BASE_URL

    if CREDS is not None:
        _LOGGER.info("Found cached credentials. Using them.")
        jsoncreds = str(base64.b64decode(CREDS), 'utf8')
        creds = MerossCloudCreds.from_json(jsoncreds)
        return await MerossHttpClient.async_from_cloud_creds(creds, **opt_params), False
    else:
        _LOGGER.info("Using username-password credentials")
        return await MerossHttpClient.async_from_user_password(email=EMAIL, password=PASSWORD, **opt_params), True
