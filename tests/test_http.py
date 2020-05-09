import os

from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from meross_iot.http_api import MerossHttpClient
from meross_iot.model.http.exception import AuthenticatedPostException

EMAIL = os.environ.get('MEROSS_EMAIL')
PASSWORD = os.environ.get('MEROSS_PASSWORD')


class TestHttpMethods(AioHTTPTestCase):
    async def get_application(self):
        return web.Application()

    async def setUpAsync(self):
        self.meross_client = await MerossHttpClient.async_from_user_password(email=EMAIL, password=PASSWORD)

    @unittest_run_loop
    async def test_subdevice_listing(self):
        devices = await self.meross_client.async_list_devices()
        # look for a msxh0 hub
        hub = None
        for d in devices:
            if d.device_type == "msh300":
                hub = d
                break

        if hub is None:
            self.skipTest("No hub was found on this subscription. Cannot test hub listing.")

        result = await self.meross_client.async_list_hub_subdevices(hub.uuid)
        self.assertGreater(len(result), 0)
        return result

    @unittest_run_loop
    async def test_bad_login(self):
        with self.assertRaises(AuthenticatedPostException):
            return await MerossHttpClient.async_from_user_password(email="wronguser@anythin.com",
                                                                   password="thisIzWRONG!")

    @unittest_run_loop
    async def test_device_listing(self):
        devices = await self.meross_client.async_list_devices()
        assert devices is not None
        assert len(devices) > 0

    async def tearDownAsync(self):
        await self.meross_client.async_logout()
