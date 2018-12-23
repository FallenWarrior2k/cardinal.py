import logging

import discord
import pytest
from discord.ext import commands
from sqlalchemy.orm import Session, sessionmaker

from cardinal.bot import Bot
from cardinal.context import Context
from cardinal.errors import UserBlacklisted


@pytest.fixture
def engine(mocker):
    return mocker.Mock()


@pytest.fixture
def baseclass_ctor(mocker):
    return mocker.patch('cardinal.bot.commands.Bot.__init__')


@pytest.fixture
def bot(baseclass_ctor, engine, mocker, request):
    kwargs = getattr(request, 'param', {})  # Use request param if provided
    return Bot(engine=engine, **kwargs)


class TestCtor:
    def test_no_game(self, baseclass_ctor, bot, engine):
        assert bot.sessionmaker.kw['bind'] is engine
        assert isinstance(bot.sessionmaker, sessionmaker)

        baseclass_ctor.assert_called_once_with(description='cardinal.py', game=None)

    @pytest.mark.parametrize(
        ['bot'],
        [
            [{'default_game': 'test 123'}]
        ],
        indirect=True
    )
    def test_game(self, baseclass_ctor, bot):
        game = discord.Game('test 123')
        baseclass_ctor.assert_called_once_with(description='cardinal.py', game=game)


@pytest.mark.asyncio
async def test_before_invoke_hook(bot, mocker):
    ctx = mocker.Mock()
    await bot.before_invoke_hook(ctx)
    assert ctx.session_allowed


@pytest.mark.asyncio
class TestAfterInvokeHook:
    @pytest.fixture
    def ctx(self, mocker):
        ctx = mocker.Mock()
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
        ctx.session.close.assert_called_once_with()

    async def test_success(self, bot, ctx):
        ctx.session_used = True
        ctx.command_failed = False
        await bot.after_invoke_hook(ctx)

        ctx.session.commit.assert_called_once_with()
        ctx.session.close.assert_called_once_with()


class TestSessionScope:
    @pytest.fixture
    def session(self, mocker):
        return mocker.Mock(spec=Session)

    @pytest.fixture
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
        with pytest.raises(Exception, message=exc_message):
            with bot.session_scope() as new_session:
                assert new_session is session
                raise exc

        sessionmaker.assert_called_once_with()
        session.rollback.assert_called_once_with()
        session.close.assert_called_once_with()


@pytest.mark.asyncio
async def test_on_ready(bot, caplog, mocker):
    mocker.patch('cardinal.bot.Bot.user', new_callable=mocker.PropertyMock, return_value='test123')
    with caplog.at_level(logging.INFO, logger='cardinal.bot'):
        await bot.on_ready()

    assert caplog.records != []


@pytest.mark.usefixtures("patches")
@pytest.mark.asyncio
class TestOnMessage:
    @pytest.fixture
    def ctx(self, mocker):
        return mocker.Mock()

    @pytest.fixture
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


@pytest.mark.asyncio
async def test_on_command(bot, caplog, mocker):
    mock_msg = 'Test message'
    format_message = mocker.patch('cardinal.bot.format_message', return_value=mock_msg)
    ctx = mocker.Mock()

    with caplog.at_level(logging.INFO, logger='cardinal.bot'):
        await bot.on_command(ctx)

    assert mock_msg in caplog.text
    format_message.assert_called_once_with(ctx.message)


@pytest.mark.asyncio
class TestOnCommandError:
    @pytest.fixture
    def clean_prefix(self, mocker):
        return mocker.patch('cardinal.bot.clean_prefix', return_value='Test prefix')

    @pytest.fixture
    def ctx(self, mocker):
        ctx = mocker.Mock()
        ctx.command.qualified_name = 'Test command name'
        ctx.message.content = 'Test message content'
        ctx.send = mocker.CoroMock()

        return ctx

    async def test_command_error(self, bot, clean_prefix, ctx, mocker):
        error = mocker.Mock(spec=commands.CommandError)
        await bot.on_command_error(ctx, error)

        clean_prefix.assert_not_called()
        ctx.send.assert_not_called()

    async def test_missing_required_argument(self, bot, clean_prefix, ctx, mocker):
        error = mocker.Mock(spec=commands.MissingRequiredArgument)
        await bot.on_command_error(ctx, error)

        clean_prefix.assert_called_once_with(ctx)
        error_msg = 'Too few arguments. Did you forget anything?\n' \
                    'See `{}help {}` for information on the command.'\
                    .format(clean_prefix.return_value, ctx.command.qualified_name)
        ctx.send.assert_called_once_with(error_msg)

    async def test_bad_argument(self, bot, clean_prefix, ctx, mocker):
        error = mocker.Mock(spec=commands.BadArgument)
        await bot.on_command_error(ctx, error)

        clean_prefix.assert_called_once_with(ctx)
        error_msg = 'Argument parsing failed. Did you mistype anything?\n' \
                    'See `{}help {}` for information on the command.'\
                    .format(clean_prefix.return_value, ctx.command.qualified_name)
        ctx.send.assert_called_once_with(error_msg)

    async def test_no_private_message(self, bot, clean_prefix, ctx, mocker):
        error = mocker.Mock(spec=commands.NoPrivateMessage)
        await bot.on_command_error(ctx, error)

        clean_prefix.assert_not_called()
        error_msg = 'Command cannot be used in private message channels.'\
            .format(clean_prefix.return_value, ctx.command.qualified_name)
        ctx.send.assert_called_once_with(error_msg)

    async def test_check_failure(self, bot, clean_prefix, ctx, mocker):
        error = mocker.MagicMock(spec=commands.CheckFailure)
        await bot.on_command_error(ctx, error)

        clean_prefix.assert_not_called()
        error_msg = 'This command cannot be used in this context.\n' \
                    '{}'.format(error.__str__.return_value)
        ctx.send.assert_called_once_with(error_msg)

    async def test_command_not_found(self, bot, clean_prefix, ctx, mocker):
        error = mocker.Mock(spec=commands.CommandNotFound)
        await bot.on_command_error(ctx, error)

        clean_prefix.assert_not_called()
        ctx.send.assert_not_called()

    async def test_disabled_command(self, bot, clean_prefix, ctx, mocker):
        error = mocker.Mock(spec=commands.DisabledCommand)
        await bot.on_command_error(ctx, error)

        clean_prefix.assert_not_called()
        ctx.send.assert_not_called()

    async def test_command_invoke_error(self, bot, caplog, clean_prefix, ctx, mocker):
        error = mocker.Mock(spec=commands.CommandInvokeError)
        error.original = mocker.MagicMock()

        with caplog.at_level(logging.ERROR, logger='cardinal.bot'):
            await bot.on_command_error(ctx, error)

        assert caplog.records != []
        clean_prefix.assert_not_called()
        error_msg = 'An error occurred while executing the command.'
        ctx.send.assert_called_once_with(error_msg)

    async def test_too_many_arguments(self, bot, clean_prefix, ctx, mocker):
        error = mocker.Mock(spec=commands.TooManyArguments)
        await bot.on_command_error(ctx, error)

        clean_prefix.assert_called_once_with(ctx)
        error_msg = 'Too many arguments. Did you miss any quotes?\n' \
                    'See `{}help {}` for information on the command.'\
                    .format(clean_prefix.return_value, ctx.command.qualified_name)
        ctx.send.assert_called_once_with(error_msg)

    async def test_user_input_error(self, bot, clean_prefix, ctx, mocker):
        error = mocker.Mock(spec=commands.UserInputError)
        await bot.on_command_error(ctx, error)

        clean_prefix.assert_called_once_with(ctx)
        error_msg = '\nSee `{}help {}` for information on the command.' \
            .format(clean_prefix.return_value, ctx.command.qualified_name)
        ctx.send.assert_called_once_with(error_msg)

    async def test_command_on_cooldown(self, bot, clean_prefix, ctx, mocker):
        error = mocker.MagicMock(spec=commands.CommandOnCooldown)
        await bot.on_command_error(ctx, error)

        clean_prefix.assert_not_called()
        error_msg = error.__str__.return_value
        ctx.send.assert_called_once_with(error_msg)

    async def test_not_owner(self, bot, clean_prefix, ctx, mocker):
        error = mocker.MagicMock(spec=commands.NotOwner)
        await bot.on_command_error(ctx, error)

        clean_prefix.assert_not_called()
        error_msg = 'This command cannot be used in this context.\n{}'\
                    .format(error.__str__.return_value)
        ctx.send.assert_called_once_with(error_msg)

    async def test_missing_permissions(self, bot, clean_prefix, ctx, mocker):
        error = mocker.MagicMock(spec=commands.MissingPermissions)
        await bot.on_command_error(ctx, error)

        clean_prefix.assert_not_called()
        error_msg = 'This command cannot be used in this context.\n{}'\
                    .format(error.__str__.return_value)
        ctx.send.assert_called_once_with(error_msg)

    async def test_bot_missing_permissions(self, bot, clean_prefix, ctx, mocker):
        error = mocker.MagicMock(spec=commands.BotMissingPermissions)
        await bot.on_command_error(ctx, error)

        clean_prefix.assert_not_called()
        error_msg = 'This command cannot be used in this context.\n{}'\
                    .format(error.__str__.return_value)
        ctx.send.assert_called_once_with(error_msg)

    async def test_user_blacklisted(self, bot, clean_prefix, ctx, mocker):
        error = mocker.Mock(spec=UserBlacklisted)
        await bot.on_command_error(ctx, error)

        clean_prefix.assert_not_called()
        ctx.send.assert_not_called()


@pytest.mark.asyncio
async def test_on_error(bot, caplog):
    with caplog.at_level(logging.ERROR, logger='cardinal.bot'):
        await bot.on_error('Test name')

    assert caplog.records != []
