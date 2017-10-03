from asyncio import coroutine
from unittest.mock import Mock


class Empty:
    """Centralised class to allow for dynamic properties."""
    pass


def CoroMock():
    coro = Mock(name="CoroutineResult")
    corofunc = Mock(name="CoroutineFunction", side_effect=coroutine(coro))
    corofunc.coro = coro
    return corofunc
