from asyncio import coroutine

import pytest


@pytest.fixture
def mocker(mocker):
    """
    Extend the global mocker fixture with a mock for coroutines.

    Args:
        mocker: Global mocker fixture as exported by pytest-mock.

    Returns:
        Modified mocker fixture that has an added `CoroMock` attribute.
    """
    def CoroMock(*args, **kwargs):
        coro = mocker.Mock(name="CoroutineResult", *args, **kwargs)
        corofunc = mocker.Mock(name="CoroutineFunction", side_effect=coroutine(coro))
        corofunc.coro = coro
        return corofunc

    mocker.CoroMock = CoroMock
    return mocker
