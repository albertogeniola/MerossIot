Quick start
===========

We (developers) all know how important is to get things working fast.
In this section, you can find some quick-reference recipies that can be used for
start working straight forward.

.. note::
   Immediately getting hands dirty with code is OK for quick demos.
   However, you should really read the entire documentation carefully in order to avoid
   gotchas. After all, someone has taken the effort of writing some documentation, why
   would you not read it?

Listing devices
---------------
In order to discover meross devices, you need to setup a :code:`MerossManager`. Once the manager has been created,
then you can invoke the :code:`async_device_discovery()` method. At that point, you can invoke the
:code:`find_device()` which allows you to list all the devices that have been discovered by the manager.

In case you want to search for specific devices, you can pass some filtering argument to this method.
Have a look at the following method signature for more details.

.. automethod:: meross_iot.manager.MerossManager.find_devices


.. literalinclude:: ../examples/readme.py
   :linenos:
   :caption: Listing Meross device
   :name: listing
   :language: python

Toggling switches
-----------------

.. literalinclude:: ../examples/toggle.py
   :linenos:
   :caption: Toggling smart switches
   :name: toggling
   :language: python


Controlling bulbs
-----------------

Reading sensors
-----------------

Controlling Thermostat
----------------------
