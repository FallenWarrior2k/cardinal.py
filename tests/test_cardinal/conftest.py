from asyncio import coroutine

import pytest


@pytest.fixture
def mocker(mocker):
    """
    Extend the global mocker fixture with a coroutine mock and non-callable mocks.

    Args:
        mocker: Global mocker fixture as exported by pytest-mock.

    Returns:
        Modified mocker fixture that additionally supports `CoroMock`,
        :class:`unittest.mock.NonCallableMock` and :class:`unittest.mock.NonCallableMagicMock`.
    """
    def CoroMock(*args, **kwargs):
        coro = mocker.Mock(name="CoroutineResult", *args, **kwargs)
        corofunc = mocker.Mock(name="CoroutineFunction", side_effect=coroutine(coro))
        corofunc.coro = coro
        return corofunc

    mocker.CoroMock = CoroMock
    mocker.NonCallableMock = mocker.mock_module.NonCallableMock
    mocker.NonCallableMagicMock = mocker.mock_module.NonCallableMagicMock
    return mocker
