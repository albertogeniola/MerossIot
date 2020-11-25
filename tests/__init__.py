import base64
import logging
import os

from typing import Tuple

from meross_iot.http_api import MerossHttpClient
from meross_iot.model.credentials import MerossCloudCreds

EMAIL = os.environ.get('MEROSS_EMAIL')
PASSWORD = os.environ.get('MEROSS_PASSWORD')
CREDS = os.getenv("__MEROSS_CREDS")


_LOGGER = logging.getLogger(__name__)


async def async_get_client() -> Tuple[MerossHttpClient, bool]:
    if CREDS is not None:
        _LOGGER.info("Found cached credentials. Using them.")
        jsoncreds = base64.b64decode(CREDS)
        creds = MerossCloudCreds.from_json(jsoncreds)
        return await MerossHttpClient.async_from_cloud_creds(creds), False
    else:
        _LOGGER.info("Using username-password credentials")
        return await MerossHttpClient.async_from_user_password(email=EMAIL, password=PASSWORD), True
