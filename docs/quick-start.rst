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
--------------------

.. literalinclude:: ../examples/toggle.py
   :linenos:
   :caption: Toggling smart switches
   :name: toggling
   :language: python

Meross devices that supports toggling and on/off commands implement the
:code:`meross_iot.controller.mixins.toggle.ToggleXMixin`. This class exposes a number of methods
to control these devices, such :code:`async_turn_off()` and :code:`async_turn_on()`.
Refer to the :doc:`ToggleXMixn <api-reference/controller/mixins/toggle>` for a panoramic around the ToggleMixin class.

Controlling bulbs
-----------------

.. literalinclude:: ../examples/light.py
   :linenos:
   :caption: Operating smart bulbs
   :name: bulbs
   :language: python

Smart bulbs implement the :code:`meross_iot.controller.mixins.light.LightMixin` interface, which handle
RGB color settings, as well as luminance and color temperature. More details on this class are available
:doc:`here <api-reference/controller/mixins/light>`

Controlling garage door openers
-------------------------------
Meross garage door openers are somehow basic: in most cases they only simulate the
button-press of the garage door. The door state is instead monitored with a specific sensor
that must be mounted on the garage door. When you operate the Meross Garage Opener, it sends the
signal to the garage motor, which starts opening/closing. Then, once the door closes, the sensor
reports "closing state", and the door is marked as closed. However, when opening the door, things
are quite different: as soon as the motor is operated, the sensor quickly reports "door opened" state
as the magnet proximity sensor immediately changes state, even if the door is not completely opened.

.. warning::
   Operating garage door is dangerous and might not be safe. You use this capability at your own risk,
   absolving the author of this library of all responsibility.

.. literalinclude:: ../examples/cover.py
   :linenos:
   :caption: Operating door opener
   :name: garage-door
   :language: python

Garage door functionality is implemented by the :code:`meross_iot.controller.mixins.garage.GarageOpenerMixin`.
Have a look at :doc:`here <api-reference/controller/mixins/garage>` for more details.

Reading sensors
----------------

Meross devices might be equipped with sensors. Some devices (like temperature and humidity sensor) are in fact
exclusively readable, configuring themselves as proper sensor devices. Others, as the MSS310, the Thermostat
valve or the garage openers are instead actuators that offer some data reading capabilities.
For this reason, there is no "general" sensor mixin class; on the contrary, you should rely on the capabilities
offered by other mixins.

The following example will show you how to read power consumption data from a
MSS310 plug, which implements both the :code:`meross_iot.controller.mixins.electricity.ElectricityMixin` and the
:code:`meross_iot.controller.mixins.consumption.ConsumptionXMixin`.

.. literalinclude:: ../examples/electricity.py
   :linenos:
   :caption: Reading power consumption
   :name: power-consumption
   :language: python

In this case, the core of the script is the method :code:`async_get_instant_metrics()` which
reads the current electricity data from the device. More details on the electricity mixin are
available :doc:`here <api-reference/controller/mixins/electricity>`

For reading data from the MS100 temperature and humidity sensor, you can rely on the following snippet.

.. literalinclude:: ../examples/sensor.py
   :linenos:
   :caption: Reading from sensor
   :name: sensor
   :language: python

More details on the specific methods offered by the Ms100 sensor device are documented
within the :doc:`Ms100Sensor class <api-reference/controller/subdevice/sensor>`.

Controlling Thermostat
----------------------

The Meross thermostat valve is operated via `meross_iot.controller.subdevice.Mts100v3Valve` class.

.. literalinclude:: ../examples/valve.py
   :linenos:
   :caption: Operating the smart valve
   :name: smart-valve
   :language: python

For more information about all the properties and methods exposed by the valve class, have a look at
:doc:`Valve reference <api-reference/controller/subdevice/valve>`