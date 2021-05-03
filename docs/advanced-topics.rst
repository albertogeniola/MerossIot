Advanced topics
===============

Managing rate limits
--------------------

Starting from version 0.4.0.4, the `MerossManager` object limits the MQTT messages sent to the Meross cloud,
in order to prevent ban from Meross security team when flooding the remote MQTT broker.

The current implementation of rate limits is based on a *global* rate limiter and on a *per device* rate limiter.
Each command issued by the manager is first checked against the device limits.
If that limit is not reached yet, then a second check is performed against the global limit.
If both the checks pass, then the command is issued.

In case any of the two limits is reached, the Manager can proceed in two ways.
If the *limit_hits/burst_rate* is **below** the `over_limit_threshold_percentage`, then the message is simply delayed of over_limit_delay_seconds.
If the *limit_hits/burst_rate* is **above** the `over_limit_threshold_percentage`, then the message is droped and `RateLimitExceeded` is raised.

Both limit checks are based on the `Token bucket policy <https://it.wikipedia.org/wiki/Token_bucket>`_ and the developer can set them up when building the `MerossManager` object.
In fact, the `MerossManager` supports the following parameters:

=============================== ============= =========================================================================
Parameter                       Default value Description
------------------------------- ------------- -------------------------------------------------------------------------
burst_requests_per_second_limit 4             Maximum number of requests that can be served in a-second burst
------------------------------- ------------- -------------------------------------------------------------------------
requests_per_second_limit       1             Number of new tokens per second
------------------------------- ------------- -------------------------------------------------------------------------
over_limit_delay_seconds        1             Seconds to delay when limit is reached
------------------------------- ------------- -------------------------------------------------------------------------
over_limit_threshold_percentage 1000          Percentage threshold above which messages are dropped rather than delayed
=============================== ============= =========================================================================

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

