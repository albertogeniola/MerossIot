import base64
import os

from meross_iot.http_api import MerossHttpClient
from meross_iot.model.credentials import MerossCloudCreds

EMAIL = os.environ.get('MEROSS_EMAIL')
PASSWORD = os.environ.get('MEROSS_PASSWORD')
CREDS = os.getenv("__MEROSS_CREDS")


async def async_get_client() -> MerossHttpClient:
    if CREDS is not None:
        jsoncreds = base64.b64decode(CREDS)
        creds = MerossCloudCreds.from_json(jsoncreds)
        return await MerossHttpClient.async_from_cloud_creds(creds)
    else:
        return await MerossHttpClient.async_from_user_password(email=EMAIL, password=PASSWORD)
