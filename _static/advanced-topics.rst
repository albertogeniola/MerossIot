Advanced topics
===============

Push notification handling
--------------------------

The current library allows a developer to catch and react to events that occur on a specific device.
The :code:`BaseDevice` class exposes the :code:`register_push_notification_handler_coroutine()` method, which
allows to register an async coroutine to be executed when an push notification is received for that device.
The registered coroutine signature must match the following signature:

.. code-block:: python

    # ... OMISSIS ...
    async def coro_name(namespace: Namespace, data: dict, device_internal_id: str):
        # TODO: do something with event data
        pass

The push notification handler can be de-registered via the :code:`unregister_push_notification_handler_coroutine()`
method, which takes as input the coroutine to unregister.

Similarly, it is possible to intercept all the push notifications received for all the devices, by registering a push
notification coroutine handler to the :code:`MerossManager` instance. This can be done using the
:code:`register_push_notification_handler_coroutine()` method and passing a coroutine definition that matches the
following signature:

.. code-block:: python

    # ... OMISSIS ...
    async def evt_coro(namespace: Namespace, data: dict, device_internal_id: str, *args, **kwargs):
        # TODO: do something with event data
        pass


.. warning::
   Failure to comply with the given signature will prevent the event handler from executing.
   Be sure to stick with the exact method signature.

Again, it is possible to de-register such push notification handlers by invoking the
:code:`unregister_push_notification_handler_coroutine()` and passing the coroutine to unregister

.. note::
   For long-running and deamon like scripts, you should limit the number of registered push notificaiton handlers
   and you should unregister when they are no more needed.

Logging
-------
This library relies on the standard Python's logging module.
It is possible to control the logging verbosity by modifying the severity of meross_iot log level, as shown
in the following example.

.. code-block:: python

    import asyncio
    import os
    import logging
    from meross_iot.http_api import MerossHttpClient
    from meross_iot.manager import MerossManager


    meross_root_logger = logging.getLogger("meross_iot")
    meross_root_logger.setLevel(logging.WARNING)

That code snippet will raise the log-level to WARNING, so DEBUG and INFO messages are not logged any longer.


Cache device registry information
-----------------

The `MerossManager` instance holds a device registry which keeps track of discovered devices.
Sometimes it might be useful to dump the information contained into the registry to reload it
when necessary. For instance, the usage of a dumped registry file can reduce the number of calls to
the Meross Cloud, as you can avoid the discovery call. An example of this approach is explained
in the `examples\\dump.py`

In particular, the registry information can be exported to the a file calling the `dump_device_registry()`.

.. code-block:: python

    # ...
    # Init the manager and issue a discovery
    manager = MerossManager(http_client=http_api_client)
    await manager.async_init()
    await manager.async_device_discovery()
    # Dump the registry information into a test.dump file
    manager.dump_device_registry("test.dump")

At the same time, the information can be reloaded using the `load_devices_from_dump()`.

.. code-block:: python

    # ...
    # Init the manager and load the dump, so that we don't need to issue a discovery
    manager = MerossManager(http_client=http_api_client)
    await manager.async_init()
    manager.load_devices_from_dump("test.dump")
    print("Registry dump loaded.")


Sniff device data
-----------------

Meross is continuously releasing new smart devices on the market.
The library has been developed in order to automatically discover and support most of the basic
functions that such devices expose. However, as new devices are released by Meross, also new feature may arise.
In such cases, you may collect low-level data using a specific sniffing tool: `meross_sniffer`.

The sniffing tool basically listens for commands that the Meross App sends to the device and registers its "responses".
In this way, one can use the sniffer tool to collect the data exchanged by the Meross App and the device.

The tool is pretty easy to use: run the program, select the device you want to sniff data from and start to
play with the devide from the Meross App. Once you have tested the feature of interest, wait a bit and then
press ENTER to stop the sniffer. The collected data will be zipped into a folder named data.zip, that you may upload
on github in order to support the feature implementation.

.. warning::
   Even though the sniffing utility has been designed to not gather user's credentials, there is no
   way to make sure the Meross App does not send sensitive information over the network. For this reason,
   you should always change your password before using this utility. It's strongly advised to create an ad-hoc
   account for this matter.

.. note::
   In case you decide to use a dedicated Meross account for the sniffing tool, make sure to remove the device
   you want to sniff from your original account and add it to your new account, which you will use for the sniffing.

In order to use the sniffing tool, perform the following:

- Create a new Meross Account to use for the sniffing tool (alternatively, change the password of your current account)
- Make sure the device you want to sniff data from/to is added to your Meross Account and is ON and ONLINE
- Start the MerossSniffing tool (with the following command)

  .. code-block:: bash

     meross_sniffer

- Log-in with your Meross credentials
- Select the device you want to gather info from and make sure its reported status is ONLINE
- Play with the device using the Meross App: make sure to test all the features of the device if that device is not yet supported by the MerossIot library
- Once done, press ENTER
- Upload the *data.zip* file that was generated in the directory where the utility has been run

