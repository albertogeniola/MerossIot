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
.. literalinclude:: ../examples/readme.py
   :linenos:
   :caption: Listing Meross device
   :name: listing
   :language: python

In order to discover meross devices, you need to setup a :code:`MerossManager`. Once the manager has been created,
then you can invoke the :code:`async_device_discovery()` method. At that point, you can invoke the
:code:`find_device()` which allows you to list all the devices that have been discovered by the manager.

In case you want to search for specific devices, you can pass some filtering argument to this method.
Have a look at the following method signature for more details.

.. automethod:: meross_iot.manager.MerossManager.find_devices

Controlling switches
-----------------

.. literalinclude:: ../examples/toggle.py
   :linenos:
   :caption: Toggling smart switches
   :name: toggling
   :language: python

Meross devices that supports toggling and on/off commands implement the
:code:`meross_iot.controller.mixins.toggle.ToggleXMixin`. This class exposes a number of methods
to control these devices, such :code:`async_turn_off()` and :code:`async_turn_on()`.
Refer to the following details for a panoramic around the ToggleMixin class.

.. autoclass:: meross_iot.controller.mixins.toggle.ToggleXMixin
   :members:

Controlling bulbs
-----------------

.. literalinclude:: ../examples/light.py
   :linenos:
   :caption: Operating smart bulbs
   :name: bulbs
   :language: python

Smart bulbs implement the `meross_iot.controller.mixins.light.LightMixin` interface, which handle
RGB color settings, as well as luminance and color temperature.

.. autoclass:: meross_iot.controller.mixins.light.LightMixin
   :members:

Reading sensors
-----------------

Controlling Thermostat
----------------------
