from pytest import fixture, mark

from cardinal.context import Context


@fixture
def scoped_session(mocker):
    return mocker.Mock()


@fixture
def base_ctor(mocker):
    return mocker.patch('cardinal.context.BaseContext.__init__')


@fixture
def ctx(base_ctor, request, scoped_session):
    kwargs = getattr(request, 'param', {})

    yield Context(scoped_session, **kwargs)
    if hasattr(request, 'param'):  # Skip unnecessary assertions
        base_ctor.assert_called_once_with(**kwargs)


@mark.parametrize(
    ['ctx'],
    [
        ({},),
        ({'asdf': 123},)
    ],
    indirect=True
)
def test_ctor(ctx, scoped_session):
    assert ctx.session is scoped_session
