Welcome to MerossIot Library's documentation!
=============================================
So you bought some Meross piece of hardware and you now want to automate stuff with that.
Well, you're in the right place.

Before using this library
=========================
Before going any further, please note that this library is meant to be used by Python developers.
If this is the first time you approach Python, then it might be a bit too hard to start working with it.
The most important thing to understand is that this library is built with async pattern in mind.
If you are not used to **asyncio** or **Python 3.5 async** patterns, you'll probably have hard time understanding
how to perform even basic tasks with this library. If that is the case, please take some time to understand
how asyncio works and how `Python leverages async programming`_

.. _Python leverages async programming: https://realpython.com/async-io-python

.. warning::
    This library was built by looking at the traffic network between Meross App and the Meross
    backends, such as HTTP api and MQTT broker. Meross did not provide any official documentation and
    you should consider this library as unofficial and unsupported by Meross.

    For this reason, you should consider this library not for production use as there is no warranty
    that Meross does not change the way it works or explicitly blocks it. So far Meross guys seem happy about that
    but you should know that it might happen.

    If you plan to rely on this library for developing 3rd party plugins (eg. building plugins
    for domotic frameworks), please let the developer know about that.

Table Of Contents
=================
.. toctree::
   :caption: Table of Contents
   :maxdepth: 2

   installation
   quick-start
   common-gotchas
   meross-arch
   advanced-topics
   api-reference/index

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
