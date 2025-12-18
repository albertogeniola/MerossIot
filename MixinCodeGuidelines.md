# Basic implementation
Mixins must extend BaseDevice class.

## Internal state
Every mixin can have internal state variables, for their specific functionalities. 
Such internal state can be updated in multiple ways:
- by triggering a manual update, via the "async_update" method.
- by receiving a push notification, via the "_async_handle_push_notification" method.
- by receiving a SystemAll update, via the "async_handle_update" method.

There are some Mixins that do not handle any internal state, as they do not need to.

## Constructor
The Mixin constructor must initialize any mixin-private state variable.
The mixin constructor must call its parent implementation.

## Frameworks methods
Every mixin has some important methods that need to be specialized/extended in order to make a Mixin well working:
- _async_handle_push_notification
- async_handle_update
- async_update

The scope of each method is described in the docstring of the BaseClass file.

The method "_async_handle_push_notification" needs to be overridden in order to correctly parse push notification directed to the device.
A meross device can implement multiple mixins: this means there might be multiple distinct push notifications being delivered to the same instance, but for different mixins.
Each mixin override the async_handle_push_notification method and calls its parent(), handling only the namespace it is in charge of.
If a mixin has correctly handled the push notification, it returns TRUE, otherwise it returns the result of the parent handling.
This creates a "bubble" mechanism, letting all mixins handle the push notification data of their competence.

The method "async_handle_update" lets other mixins, or the manager, notify new state refreshes or manual state updates (not push notifications).
For instance, this method is called by a special Mixin, i.e. "SystemAllMixin", to refresh some instance-specific data.
The SystemAll namespace includes, in general, the entire state of the device, including all mixins involved. 
When a "GET SystemAll" command is issued on a specific device, the response is published via the SystemAllMixin to all the mixins of the device.
This allows all the mixins to update their state without sending single updates commands for every mixin.

The method "async_update" is overridden whenever there is specific mixin-local state that is not updated via the SystemAll updates received by the SystemAllMixins towards async_handle_update call.
If a Mixin offers specific state that is not handled/updated via SystemAll Namespace, this method should be overridden so that it takes care of calling its super implementation and then update the local state.

*Note*: the data pushed to _async_handle_push_notification might differ from the payloads passed the async_handle_update, even if the data namespace is the same.

## State getter methods
All the methods that provide access to mixins internal state must be implemented as properties.
In case the data returned by the state is mutable (lists, objects, etc), the getter should return a copy; the user should not be able to manipulate the internal state of the Mixins.
In cases the data returned is not mutable (int, float, boolean, etc)
All getter methods must be decorated with the "ensure_full_update" decoration, so that it checks a full update has been performed on the instance before accessing its methods.


## Naming convention
- The Mixin class name must end with "Mixin" suffix and be expressed in CamelCasing with first capital letter (e.g. "DiffuserSprayMixin").
- Private state variables must be prefixed with "__" so to keep them private to the Mixin (e.g. "__diffuser_spray_status_by_channel").
- Public mixin methods must be prefixed with the mixin class in "snake casing" (e.g. "diffuser_spray_get_name"), so that there is no possibility two distinct mixins have the same public method name.
- All async methods must be prefixed with the "async" keyword to make it evident they are async (e.g. "async_diffuser_spray_set_mode").
- If a method performs a get operation that involves sending commands to the MerossCloud, it should include the word "fetch" in its name, so that it makes clear it involves a fetch operation.
- If a method is a getter of local state, it should be implemented as a property and should not include the GET or FETCH verb in its name. 

# Code styling
- Public methods and classes must be commented.
- Type hinting is mandatory whenever needed for the type checked/linter.
- Private state variable must be prefixed with "__"

# Testing and coverage
- Mixins must be covered by unit tests via pytest.
- Coverage should be 100%
- Mixin tests are located within tests/mixins/*
- Mixin testing takes advantage of fixtures, located in tests/fixtures. Each subfolder represents a class of fixtures. Fixtures can contain placeholder templates, such as: UUID, MAC_ADDRESS, WIFI_MAC, INNER_IP, USER_ID, and so on, in the form of "${name}". Such placeholder need to be handled at test-time, for instance using "replacer_mock". 
    - handle_update folder: contains the json payload of the SYSTEM_ALL response, as the "async_handle_update" would do; each file is named after the device_type it refers to.
    - mqtt_response_payloads folder: contains the response payloads for specific commands being issued; each file is named after "COMMAND.NAMESPACE_VARIANT.json". Command can either be SET or GET; NAMESPACE is derived by the specific namespace value, without the leading "Appliance." prefix; VARIANT represents the specific variant for the state (e.g. STRONG if the current payload represents a DIFFUSER SPRAY in the state "STRONG", or "OFF" if the current payload refers to a switch in the OFF state).
    - push_notifications folder: contains the push notifications fixtures for specific mixins, in the form "mixinname-variant.json"
  