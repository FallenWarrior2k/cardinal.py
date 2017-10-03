from asyncio import coroutine
from unittest.mock import Mock


def CoroMock(*args, **kwargs):
    coro = Mock(name="CoroutineResult", *args, **kwargs)
    corofunc = Mock(name="CoroutineFunction", side_effect=coroutine(coro))
    corofunc.coro = coro
    return corofunc
