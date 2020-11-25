import os

from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from meross_iot.http_api import MerossHttpClient
from meross_iot.model.http.exception import BadLoginException
from tests import async_get_client

if os.name == 'nt':
    import asyncio

    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
else:
    import asyncio


class TestHttpMethods(AioHTTPTestCase):
    async def get_application(self):
        return web.Application()

    async def setUpAsync(self):
        # Wait some time before next test-burst
        await asyncio.sleep(10)
        self.meross_client, self.requires_logout = await async_get_client()

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
        with self.assertRaises(BadLoginException):
            return await MerossHttpClient.async_from_user_password(email="wronguser@anythin.com",
                                                                   password="thisIzWRONG!")

    @unittest_run_loop
    async def test_device_listing(self):
        devices = await self.meross_client.async_list_devices()
        assert devices is not None
        assert len(devices) > 0

    async def tearDownAsync(self):
        if self.requires_logout:
            await self.meross_client.async_logout()
