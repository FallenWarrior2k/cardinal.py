import pytest

from cardinal.context import Context
from cardinal.errors import IllegalSessionUse


@pytest.fixture
def base_ctor(mocker):
    return mocker.patch('cardinal.context.commands.Context.__init__')


@pytest.fixture
def ctx(base_ctor, request):
    kwargs = getattr(request, 'param', {})

    yield Context(**kwargs)
    if hasattr(request, 'param'):
        base_ctor.assert_called_once_with(**kwargs)  # Skip unnecessary assertions


@pytest.fixture
def sessionmaker(ctx, mocker):
    ctx.bot = mocker.Mock()
    return ctx.bot.sessionmaker


@pytest.mark.parametrize(
    ['ctx'],
    [
        ({},),
        ({'asdf': 123},)
    ],
    indirect=True
)
def test_ctor(ctx):
    assert not ctx.session_used


def test_session_not_allowed(ctx, sessionmaker):
    with pytest.raises(IllegalSessionUse):
        _ = ctx.session

    sessionmaker.assert_not_called()


def test_session_allowed(ctx, sessionmaker):
    ctx.session_allowed = True

    sess1 = ctx.session

    sessionmaker.assert_called_once_with()
    assert ctx.session_used is True

    sessionmaker.reset_mock()
    sess2 = ctx.session
    sessionmaker.assert_not_called()

    assert sess1 is sess2
