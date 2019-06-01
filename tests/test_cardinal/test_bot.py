import logging

from discord import Game
from discord.ext.commands import (
    BadArgument, BotMissingPermissions, CheckFailure, CommandError, CommandInvokeError,
    CommandNotFound, CommandOnCooldown, DisabledCommand, MissingPermissions,
    MissingRequiredArgument, NoPrivateMessage, NotOwner, TooManyArguments, UserInputError
)
from pytest import fixture, mark, raises
from sqlalchemy.orm import Session, sessionmaker

from cardinal.bot import Bot
from cardinal.context import Context
from cardinal.errors import UserBlacklisted


@fixture
def engine(mocker):
    return mocker.Mock()


@fixture
def baseclass_ctor(mocker):
    return mocker.patch('cardinal.bot.BaseBot.__init__')


@fixture
def bot(baseclass_ctor, engine, mocker, request):
    kwargs = getattr(request, 'param', {})  # Use request param if provided
    return Bot(engine=engine, **kwargs)


class TestCtor:
    def test_no_game(self, baseclass_ctor, bot, engine):
        assert bot.sessionmaker.kw['bind'] is engine
        assert isinstance(bot.sessionmaker, sessionmaker)

        baseclass_ctor.assert_called_once_with(description='cardinal.py', game=None)

    @mark.parametrize(
        ['bot'],
        [
            [{'default_game': 'test 123'}]
        ],
        indirect=True
    )
    def test_game(self, baseclass_ctor, bot):
        game = Game('test 123')
        baseclass_ctor.assert_called_once_with(description='cardinal.py', game=game)


@mark.asyncio
async def test_before_invoke_hook(bot, mocker):
    ctx = mocker.Mock()
    await bot.before_invoke_hook(ctx)
    assert ctx.session_allowed


@mark.asyncio
class TestAfterInvokeHook:
    @fixture
    def ctx(self, mocker):
        ctx = mocker.Mock(spec=Context)
        ctx.session = mocker.Mock(spec=Session)
        return ctx

    async def test_unused(self, bot, ctx):
        ctx.session_used = False
        await bot.after_invoke_hook(ctx)

        assert ctx.session.mock_calls == []  # Assert mock hasn't been touched

    async def test_failed(self, bot, ctx):
        ctx.session_used = True
        ctx.command_failed = True
        await bot.after_invoke_hook(ctx)

        ctx.session.rollback.assert_called_once_with()

    async def test_success(self, bot, ctx):
        ctx.session_used = True
        ctx.command_failed = False
        await bot.after_invoke_hook(ctx)

        ctx.session.commit.assert_called_once_with()

    async def test_cleanup(self, bot, ctx, mocker):
        ctx.session_used = True
        ctx.command_failed = False  # Irrelevant, tested above
        invalidate = mocker.patch('lazy.lazy.invalidate')
        await bot.after_invoke_hook(ctx)

        assert ctx.session_allowed is False
        invalidate.assert_called_once_with(ctx, 'session')
        ctx.session.close.assert_called_once_with()


class TestSessionScope:
    @fixture
    def session(self, mocker):
        return mocker.Mock(spec=Session)

    @fixture
    def sessionmaker(self, bot, mocker, session):
        return mocker.patch.object(bot, 'sessionmaker', return_value=session)

    def test_no_exception(self, bot, session, sessionmaker):
        with bot.session_scope() as new_session:
            assert new_session is session

        sessionmaker.assert_called_once_with()
        session.commit.assert_called_once_with()
        session.close.assert_called_once_with()

    def test_exception(self, bot, session, sessionmaker):
        exc_message = 'Test exception message'
        exc = Exception(exc_message)
        with raises(Exception, match=exc_message):
            with bot.session_scope() as new_session:
                assert new_session is session
                raise exc

        sessionmaker.assert_called_once_with()
        session.rollback.assert_called_once_with()
        session.close.assert_called_once_with()


@mark.asyncio
async def test_on_ready(bot, caplog, mocker):
    mocker.patch('cardinal.bot.Bot.user', new_callable=mocker.PropertyMock, return_value='test123')
    with caplog.at_level(logging.INFO, logger='cardinal.bot'):
        await bot.on_ready()

    assert caplog.records != []


@mark.usefixtures("patches")
@mark.asyncio
class TestOnMessage:
    @fixture
    def ctx(self, mocker):
        return mocker.Mock()

    @fixture
    def patches(self, bot, ctx, mocker):
        mocker.patch.object(bot, 'get_context', new_callable=mocker.CoroMock, return_value=ctx)
        mocker.patch.object(bot, 'invoke', new_callable=mocker.CoroMock)

    async def test_not_bot(self, bot, ctx, mocker):
        msg = mocker.Mock()
        msg.author.bot = False

        await bot.on_message(msg)

        bot.get_context.assert_called_once_with(msg, cls=Context)
        bot.invoke.assert_called_once_with(ctx)

    async def test_bot(self, bot, mocker):
        msg = mocker.Mock()
        msg.author.bot = True

        await bot.on_message(msg)
        bot.get_context.assert_not_called()
        bot.invoke.assert_not_called()


@mark.asyncio
async def test_on_command(bot, caplog, mocker):
    mock_msg = 'Test message'
    format_message = mocker.patch('cardinal.bot.format_message', return_value=mock_msg)
    ctx = mocker.Mock()

    with caplog.at_level(logging.INFO, logger='cardinal.bot'):
        await bot.on_command(ctx)

    assert mock_msg in caplog.text
    format_message.assert_called_once_with(ctx.message)


@mark.asyncio
class TestOnCommandError:
    @fixture
    def clean_prefix(self, mocker):
        return mocker.patch('cardinal.bot.clean_prefix', return_value='Test prefix')

    @fixture
    def ctx(self, mocker):
        ctx = mocker.Mock()
        ctx.command.qualified_name = 'Test command name'
        ctx.message.content = 'Test message content'
        ctx.send = mocker.CoroMock()

        return ctx

    async def test_command_error(self, bot, clean_prefix, ctx, mocker):
        error = mocker.Mock(spec=CommandError)
        await bot.on_command_error(ctx, error)

        clean_prefix.assert_not_called()
        ctx.send.assert_not_called()

    async def test_missing_required_argument(self, bot, clean_prefix, ctx, mocker):
        error = mocker.Mock(spec=MissingRequiredArgument)
        await bot.on_command_error(ctx, error)

        clean_prefix.assert_called_once_with(ctx)
        error_msg = 'Too few arguments. Did you forget anything?\n' \
                    f'See `{clean_prefix.return_value}help {ctx.command.qualified_name}` ' \
                    'for information on the command.'
        ctx.send.assert_called_once_with(error_msg)

    async def test_bad_argument(self, bot, clean_prefix, ctx, mocker):
        error = mocker.Mock(spec=BadArgument)
        await bot.on_command_error(ctx, error)

        clean_prefix.assert_called_once_with(ctx)
        error_msg = 'Argument parsing failed. Did you mistype anything?\n' \
                    f'See `{clean_prefix.return_value}help {ctx.command.qualified_name}` ' \
                    'for information on the command.'
        ctx.send.assert_called_once_with(error_msg)

    async def test_no_private_message(self, bot, clean_prefix, ctx, mocker):
        error = mocker.Mock(spec=NoPrivateMessage)
        await bot.on_command_error(ctx, error)

        clean_prefix.assert_not_called()
        error_msg = 'Command cannot be used in private message channels.'
        ctx.send.assert_called_once_with(error_msg)

    async def test_check_failure(self, bot, clean_prefix, ctx, mocker):
        error = mocker.MagicMock(spec=CheckFailure)
        await bot.on_command_error(ctx, error)

        clean_prefix.assert_not_called()
        error_msg = 'This command cannot be used in this context.\n' \
                    f'{error.__str__.return_value}'
        ctx.send.assert_called_once_with(error_msg)

    async def test_command_not_found(self, bot, clean_prefix, ctx, mocker):
        error = mocker.Mock(spec=CommandNotFound)
        await bot.on_command_error(ctx, error)

        clean_prefix.assert_not_called()
        ctx.send.assert_not_called()

    async def test_disabled_command(self, bot, clean_prefix, ctx, mocker):
        error = mocker.Mock(spec=DisabledCommand)
        await bot.on_command_error(ctx, error)

        clean_prefix.assert_not_called()
        ctx.send.assert_not_called()

    async def test_command_invoke_error(self, bot, caplog, clean_prefix, ctx, mocker):
        error = mocker.Mock(spec=CommandInvokeError)
        error.original = mocker.MagicMock()

        with caplog.at_level(logging.ERROR, logger='cardinal.bot'):
            await bot.on_command_error(ctx, error)

        assert caplog.records != []
        clean_prefix.assert_not_called()
        error_msg = 'An error occurred while executing the command.'
        ctx.send.assert_called_once_with(error_msg)

    async def test_too_many_arguments(self, bot, clean_prefix, ctx, mocker):
        error = mocker.Mock(spec=TooManyArguments)
        await bot.on_command_error(ctx, error)

        clean_prefix.assert_called_once_with(ctx)
        error_msg = 'Too many arguments. Did you miss any quotes?\n' \
                    f'See `{clean_prefix.return_value}help {ctx.command.qualified_name}` ' \
                    'for information on the command.'
        ctx.send.assert_called_once_with(error_msg)

    async def test_user_input_error(self, bot, clean_prefix, ctx, mocker):
        error = mocker.Mock(spec=UserInputError)
        await bot.on_command_error(ctx, error)

        clean_prefix.assert_called_once_with(ctx)
        error_msg = f'\nSee `{clean_prefix.return_value}help {ctx.command.qualified_name}` ' \
            f'for information on the command.'
        ctx.send.assert_called_once_with(error_msg)

    async def test_command_on_cooldown(self, bot, clean_prefix, ctx, mocker):
        error = mocker.MagicMock(spec=CommandOnCooldown)
        await bot.on_command_error(ctx, error)

        clean_prefix.assert_not_called()
        error_msg = error.__str__.return_value
        ctx.send.assert_called_once_with(error_msg)

    async def test_not_owner(self, bot, clean_prefix, ctx, mocker):
        error = mocker.MagicMock(spec=NotOwner)
        await bot.on_command_error(ctx, error)

        clean_prefix.assert_not_called()
        error_msg = f'This command cannot be used in this context.\n{error.__str__.return_value}'
        ctx.send.assert_called_once_with(error_msg)

    async def test_missing_permissions(self, bot, clean_prefix, ctx, mocker):
        error = mocker.MagicMock(spec=MissingPermissions)
        await bot.on_command_error(ctx, error)

        clean_prefix.assert_not_called()
        error_msg = f'This command cannot be used in this context.\n{error.__str__.return_value}'
        ctx.send.assert_called_once_with(error_msg)

    async def test_bot_missing_permissions(self, bot, clean_prefix, ctx, mocker):
        error = mocker.MagicMock(spec=BotMissingPermissions)
        await bot.on_command_error(ctx, error)

        clean_prefix.assert_not_called()
        error_msg = f'This command cannot be used in this context.\n{error.__str__.return_value}'
        ctx.send.assert_called_once_with(error_msg)

    async def test_user_blacklisted(self, bot, clean_prefix, ctx, mocker):
        error = mocker.Mock(spec=UserBlacklisted)
        await bot.on_command_error(ctx, error)

        clean_prefix.assert_not_called()
        ctx.send.assert_not_called()


@mark.asyncio
async def test_on_error(bot, caplog):
    with caplog.at_level(logging.ERROR, logger='cardinal.bot'):
        await bot.on_error('Test name')

    assert caplog.records != []
