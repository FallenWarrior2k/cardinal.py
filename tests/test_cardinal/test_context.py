import pytest

from cardinal.context import Context
from cardinal.errors import IllegalSessionUse


@pytest.fixture
def base_ctor(mocker):
    return mocker.patch('cardinal.context.commands.Context.__init__')


@pytest.fixture(params=[
    {},
    {'asdf': 123}
])
def ctx(base_ctor, request):
    yield Context(**request.param)
    base_ctor.assert_called_once_with(**request.param)


@pytest.fixture
def sessionmaker(ctx, mocker):
    ctx.bot = mocker.Mock()
    return ctx.bot.sessionmaker


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
