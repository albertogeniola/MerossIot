Common gotchas
==============

There are a number of common error that you might be experiencing when approaching to this library
for the first time. In this section, we enumerate the known ones and we'll keep updating it as new
ones are discovered.

RuntimeError: Event loop is closed
    This error occurs when you are running this library with Python 3.8 on a Windows machine.
    The cause of this error is related to ProactorEventLoop which is used on Python 3.8.
    To solve that, you can setup asyncio library to use a different event loop implementation, which does not
    cause that error. To do so, add this line on top of your script

    .. code-block:: python

        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

Calling awaitable the wrong way
    This library implements the asyncio pattern. As a result, you should be aware of how to
    call asynchronous methods. Calling an asynchronous method without the preceding `await`
    keyword does not actually invoke the method.

Too many tokens
    This error occurs when your account has logged in many times against the Meross Cloud endpoint without
    releasing any previously acquired token.
    This is usually caused by an abuse of the `MerossManager` or the `MerossHttpClient` classes: when using these
    classes, the developer must close() / logout() the object before ending the script.
    In order to avoid hitting this API error, make sure to always invoke close()/logout() methods before ending the
    script.

    .. warning::
        The Meross API usually blocks the user for 12/24 hours when reaching the token limit.
        After 12/24 hours, the API starts working again.

Inconsistent device state
    The current implementation of the library keeps the device status aligned by listening to PUSH notifications
    received from the Meross MQTT broker. However, the first time the developer accesses the device state,
    the device state may be inconsistent. For this reason, each device implements the `async_update()` method,
    which fetches the complete device state. From that moment on, the library automatically handles state update
    by listening for push notifications.

    There are some edge cases in which the device state could become inconsistent. This happens, for instance,
    when the MerossManager looses the connection to the MQTT broker and someone else changes the device state
    (e.g. someone using the Meross app. In this case, the MerossManager looses the PUSH notification message
    as it's disconnected while the app sends the command to the device.

    To avoid such situations, developers should call the `async_update()` every time the internet connection is
    lost and then restored.


Ban from Meross cloud
    Meross security team may suspend the user accounts that perform too many requests.
    In some cases, an automated email is delivered to the email address of the user account,
    warning him about imminent suspension. In other cases, the account might be suspended without any notice.
    If that happens, the user need to contact Meross team and ask for ban-removal.
    In any case, to prevent that from happening, be sure to adopt convenient rate-limits,
    as introduced in version 0.4.0.4.

    At the time of writing, such rate limits are not documented. The MerossManager automatically applies conservative
    limits in order to prevent banning from Meross Cloud, however it's up to the Developer to properly configure
    the rate limits as explained in :ref:`advanced-topics:Managing rate limits`.

