import os

from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from meross_iot.http_api import MerossHttpClient
from meross_iot.model.http.error_codes import ErrorCodes
from meross_iot.model.http.exception import BadLoginException, BadDomainException, HttpApiError, MissingMFA, WrongMFA
from tests import async_get_client, _TEST_EMAIL, _TEST_PASSWORD, _TEST_API_BASE_URL, _TEST_EMAIL_MFA

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
        print(f"Testing device {hub.dev_name}")
        result = await self.meross_client.async_list_hub_subdevices(hub.uuid)
        if len(result) < 1:
            self.skipTest("No subdevice found for selected hub")
            return
        self.assertGreater(len(result), 0)
        return result

    @unittest_run_loop
    async def test_bad_login(self):
        with self.assertRaises(BadLoginException):
            return await MerossHttpClient.async_from_user_password(api_base_url=_TEST_API_BASE_URL,
                                                                   email=_TEST_EMAIL,
                                                                   password="thisIzWRONG!")

    @unittest_run_loop
    async def test_not_existing_email(self):
        with self.assertRaises(HttpApiError):
            try:
                return await MerossHttpClient.async_from_user_password(api_base_url=_TEST_API_BASE_URL,
                                                                       email="thisDoesNotExistIGuess@gmail.com",
                                                                       password="thisIzWRONG!")
            except HttpApiError as e:
                self.assertEqual(e.error_code, ErrorCodes.CODE_WRONG_EMAIL)
                raise e

    @unittest_run_loop
    async def test_bad_email(self):
        with self.assertRaises(HttpApiError):
            try:
                return await MerossHttpClient.async_from_user_password(api_base_url=_TEST_API_BASE_URL,
                                                                       email="invalidemail",
                                                                       password="somePassword")
            except HttpApiError as e:
                self.assertEqual(e.error_code, ErrorCodes.CODE_WRONG_EMAIL)
                raise e

    @unittest_run_loop
    async def test_missing_mfa(self):
        with self.assertRaises(MissingMFA):
            return await MerossHttpClient.async_from_user_password(api_base_url=_TEST_API_BASE_URL,
                                                                   email=_TEST_EMAIL_MFA,
                                                                   password=_TEST_PASSWORD)

    @unittest_run_loop
    async def test_wrong_mfa(self):
        with self.assertRaises(WrongMFA):
            return await MerossHttpClient.async_from_user_password(api_base_url=_TEST_API_BASE_URL,
                                                                   email=_TEST_EMAIL_MFA,
                                                                   password=_TEST_PASSWORD,
                                                                   mfa_code="invalid")

    @unittest_run_loop
    async def test_device_listing(self):
        devices = await self.meross_client.async_list_devices()
        assert devices is not None
        assert len(devices) > 0


    @unittest_run_loop
    async def test_bad_domain(self):
        with self.assertRaises(BadDomainException):
            return await MerossHttpClient.async_from_user_password(api_base_url="iot.meross.com", email=_TEST_EMAIL, password=_TEST_PASSWORD, auto_retry_on_bad_domain=False)


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
        print(f"Testing device {hub.dev_name}")
        result = await self.meross_client.async_list_hub_subdevices(hub.uuid)
        self.assertGreater(len(result), 0)
        return result

    async def tearDownAsync(self):
        if self.requires_logout:
            await self.meross_client.async_logout()
