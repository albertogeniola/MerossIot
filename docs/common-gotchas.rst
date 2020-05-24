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

Too many tokens
    TODO