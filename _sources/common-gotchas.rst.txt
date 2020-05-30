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

