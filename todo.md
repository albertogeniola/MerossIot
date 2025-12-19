This document describes the improvements to implement on the library.

# Notify State Updates

At the moment, the library offers no way to determine something has changed
in the device's internal state. Some users of this library might want to 
hook to update-events in order to react to those changes. This is especially
useful for HomeAssistant. Current HomeAssistant implementation relies on the 
push-notification handler: every time a push notification is received, the 
HA entity refreshes its internal state. This is suboptimal as there might be
some cases in which the internal state of the devices changes because of other 
factors unrelated to push notifications. For instance, power monitoring devices, 
dnd, and so on: they are fetched manually. 

The proposed change is to implement a subscribe/notify approach within the 
BaseDevice class, using a "protected" method (e.g. "_notify_state_change") and
subscribe/unsubscribe methods for listeners.
SubClasses or Mixins would call this method everytime the internal state is 
updated/changed. Subscribers would then be notified of the change. 

SubClasses and mixins must call the "_notify_state_change" method when a fetch operation 
occurs and the internal mixin state is updated. 

Special care must be taken when handling _async_handle_push_notification, async_handle_update
and async_update. The method "_async_handle_push_notification" implements a bubble-up
design: firstly it handles local state, then it calls the super implementation. 
We don't want to trigger the "_notify_state_change" on every level of the 
bubble (call stack). Therefore, we will just call the _notify_state_change method at 
the root (BaseClass) level. This might not be ideal in the case the push_notification is 
dispatched to a device that is not able to handle that as there is no way for the BaseClass
"_async_handle_push_notification" to know whether the state is going to change due to
subclasses _async_handle_push_notification implementation. To solve this issue, we can
add a new parameter to the "_async_handle_push_notification", such as "_subclass_handled" 
(defaulting to None). Everytime a subclass overrides "_async_handle_push_notification",
if the local handling has caused state change, it will call the super()._async_handle_push_notification
passing "subclass_handled=True or _subclass_handled" as argument. In this way if that 
handling or a sub-one has already caused state change, the information is brought to the
BaseClass implementation, which will then call the "_notify_state_change" method.

The implementation of async_handle_update should follow the same guidelines for 
_async_handle_push_notification. In fact, this method implements the same bubbling
approach and current implementation take care of handling local state before calling
the super() implementation. That means we can call the _notify_state_change method
from the BaseClass implementation, given that at least one of the sub-classes has
updated its state.

Regarding async_update, we don't need to invoke the _notify_state_change. In fact, 
the async_update will call other fetch methods, which are already in charge of
calling the _notify_state_change, if needed. 

# Customize communication transport
The MerossManager should be able to handle direct communication with the Meross devices
if they are in the same network, relying on direct HTTP communication. The current 
implementation partially handles this requirement. We need to further improve the logic.

The user of the library must be able to customize the communication method to use for 
issuing commands to the devices. Specifically, we want to let the user choose one of the 
following:
1. HTTP First, MQTT fall back
2. MQTT Only
3. Automatic (default)

This setting should be configured at a Global Level (MerossManager), but there should be 
the possibility to override it on every device.

Whenever a command is issued to the device, the library should check if a per-device preference
has been specified. If not, the library should fall back to the global preference set at Manager
level. By default, the Manager will use "Automatic" mode.

## HTTP First, MQTT fall back
The "Prefer HTTP" option will cause the library to try to use direct HTTP communication
with the device, by leveraging the "lan_ip" address attribute, if set.
We need to add a new method in the BaseDevice that tests for "LAN line of sight": this 
method should issue a SYSTEM_ALL request against the device using HTTP transport with a 
short Timeout (1s). By doing so, we are able to test the visibility of the device in the
local network. The manager should also re-issue the check whenever the ONLINE state of the 
device changes or whenever an async_update() method is called on the base-device.

If a command fails to be delivered over HTTP, the manager must then re-issue the same command 
via MQTT broker, and keep count of failed attempts. 

## MQTT Only
This mode requires all commands to be issued via MQTT, even if the device is reachable 
by LAN communication.

## Automatic
The automatic mode is based on tracking the HTTP failures and decide when it is better
to move to MQTT only, without trying the HTTP request. In other words, the manager must
keep track of failed attempts to reach a specific device over HTTP and dynamically change
its communication strategy. Specifically, if three consequent HTTP attempts fail, then 
the strategy should change to "MQTT Only", until the "online" state varies (goes offline 
and comes back online). 

Whenever there is a change of strategy, there should be appropriate log entries.
