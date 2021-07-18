from multiprocessing import Process

import socks
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from meross_iot.controller.device import BaseDevice
from meross_iot.controller.known.subdevice import Mts100v3Valve
from meross_iot.controller.mixins.toggle import ToggleXMixin
from meross_iot.manager import MerossManager
from meross_iot.model.enums import OnlineStatus, Namespace
from meross_iot.model.push.online import OnlinePushNotification
from tests import async_get_client
import os
from proxy import proxy

PROXY_PORT = 5001

if os.name == 'nt':
    import asyncio

    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
else:
    import asyncio


class ProxyManager:
    def __init__(self, port):
        self._port = port
        self._process = None
        self._started = False

    def start(self):
        if not self._started:
            self._process = Process(target=proxy.main, args=(['--port', str(self._port)],))
            self._process.start()
            self._started = True

    def stop(self):
        if self._started:
            self._process.terminate()
            self._process.join(5)
            if self._process.exitcode is None:
                self._process.kill()
            self._process = None
            self._started = False


class TestDisconnection(AioHTTPTestCase):
    async def get_application(self):
        return web.Application()

    async def setUpAsync(self):
        # Setup the proxy
        self._proxy = ProxyManager(port=PROXY_PORT)
        self._proxy.start()

        # Wait some time before next test-burst
        await asyncio.sleep(10)
        self.meross_client, self.requires_logout = await async_get_client()
        self.meross_client.set_http_proxy(f"http://localhost:{PROXY_PORT}")

        self.meross_manager = MerossManager(http_client=self.meross_client)
        self.meross_manager.set_proxy(proxy_type=socks.HTTP, proxy_addr="localhost", proxy_port=PROXY_PORT)

        await self.meross_manager.async_init()
        await self.meross_manager.async_device_discovery()
        self.test_devices = self.meross_manager.find_devices(device_class=ToggleXMixin,
                                                             online_status=OnlineStatus.ONLINE)

    @unittest_run_loop
    async def test_disconnect(self):
        if len(self.test_devices) < 1:
            self.skipTest("No ToggleX device has been found to run this test on.")

        # Select the first device
        dev = self.test_devices[0]  # type: BaseDevice
        await dev.async_update()

        # Register a connection reset event handler
        disconnection_event = asyncio.Event()
        connection_event = asyncio.Event()

        async def evt_coro(namespace: Namespace, data: dict, device_internal_id: str, *args, **kwargs):
            if namespace == Namespace.SYSTEM_ONLINE:
                status = OnlineStatus(int(data.get('online').get('status')))
                if not disconnection_event.is_set() and status == OnlineStatus.UNKNOWN:
                    disconnection_event.set()
                elif not connection_event.is_set() and status == OnlineStatus.ONLINE:
                    connection_event.set()

        dev.register_push_notification_handler_coroutine(evt_coro)
        self._proxy.stop()

        try:
            await asyncio.wait_for(disconnection_event.wait(), 90.0)
        except asyncio.TimeoutError:
            self.fail("Disconnection was not triggered.")

        # Ok, disconnection was triggered. Let's now re-enable the proxy and wait for devices coming online again...
        self._proxy.start()
        await asyncio.sleep(10)
        # Let's wait for connection to be re-established
        try:
            await asyncio.wait_for(connection_event.wait(), 90.0)
        except asyncio.TimeoutError:
            self.fail("Connection was not triggered.")

    async def tearDownAsync(self):
        if self.requires_logout:
            await self.meross_client.async_logout()

        self._proxy.stop()
