import logging
from functools import partial

from discord import Game
from discord.ext.commands import (
    BadArgument,
    BotMissingPermissions,
    CheckFailure,
    CommandError,
    CommandInvokeError,
    CommandNotFound,
    CommandOnCooldown,
    DisabledCommand,
    MissingPermissions,
    MissingRequiredArgument,
    NoPrivateMessage,
    NotOwner,
    TooManyArguments,
    UserInputError,
)
from pytest import fixture, mark, raises

from cardinal.bot import Bot, intents
from cardinal.context import Context
from cardinal.errors import UserBlacklisted


@fixture
def event_context(mocker):
    return mocker.patch("cardinal.bot.event_context")


@fixture
def scoped_session(mocker):
    return mocker.Mock()


@fixture
def context_factory(scoped_session):
    return partial(Context, scoped_session)


@fixture
def baseclass_ctor(mocker):
    return mocker.patch("cardinal.bot.BaseBot.__init__")


@fixture
def bot(baseclass_ctor, context_factory, mocker, request, scoped_session):
    kwargs = {
        "context_factory": context_factory,
        "default_game": None,
        "scoped_session": scoped_session,
    }
    kwargs.update(getattr(request, "param", {}))  # Use request param if provided

    return Bot(**kwargs)


class TestCtor:
    def test_no_game(self, baseclass_ctor, bot):
        baseclass_ctor.assert_called_once_with(
            description="cardinal.py", game=None, intents=intents
        )

    @mark.parametrize(["bot"], [[{"default_game": "test 123"}]], indirect=True)
    def test_game(self, baseclass_ctor, bot):
        game = Game("test 123")
        baseclass_ctor.assert_called_once_with(
            description="cardinal.py", game=game, intents=intents
        )

    def test_attributes(self, bot, context_factory, scoped_session):
        assert bot._context_factory is context_factory
        assert bot._event_counter == 0
        assert bot._session is scoped_session


@mark.asyncio
class TestRunEvent:
    @fixture
    def run_event(self, mocker, request):
        kwargs = getattr(request, "param", {})
        return mocker.patch(
            "cardinal.bot.BaseBot._run_event", new_callable=mocker.CoroMock, **kwargs
        )

    async def test_no_exception(self, bot, event_context, run_event, scoped_session):
        args = (1, 2, 3)
        kwargs = {"a": "b", "c": "d"}

        await bot._run_event(*args, **kwargs)

        run_event.assert_called_once_with(*args, **kwargs)
        event_context.set.assert_called_once_with(bot._event_counter)
        scoped_session.remove.assert_called_once_with()

    @mark.parametrize(["run_event"], [[{"side_effect": Exception()}]], indirect=True)
    async def test_exception(self, run_event, bot, scoped_session):
        with raises(Exception):
            await bot._run_event()

        scoped_session.remove.assert_called_once_with()


@mark.asyncio
async def test_on_ready(bot, caplog, mocker):
    mocker.patch(
        "cardinal.bot.Bot.user",
        new_callable=mocker.PropertyMock,
        return_value="test123",
    )
    with caplog.at_level(logging.INFO, logger="cardinal.bot"):
        await bot.on_ready()

    assert caplog.records != []


@mark.usefixtures("patches")
@mark.asyncio
class TestOnMessage:
    @fixture
    def ctx(self, mocker):
        return mocker.Mock()

    @fixture
    def msg(self, mocker):
        msg = mocker.Mock()
        # Prevent accidental short-circuits
        msg.author.bot = False

        return msg

    @fixture
    def patches(self, bot, ctx, mocker):
        mocker.patch.object(
            bot, "get_context", new_callable=mocker.CoroMock, return_value=ctx
        )
        mocker.patch.object(bot, "invoke", new_callable=mocker.CoroMock)

    async def test_not_bot(self, bot, context_factory, ctx, msg):
        await bot.on_message(msg)

        bot.get_context.assert_called_once_with(msg, cls=context_factory)
        bot.invoke.assert_called_once_with(ctx)

    async def test_bot(self, bot, msg):
        msg.author.bot = True

        await bot.on_message(msg)
        bot.get_context.assert_not_called()
        bot.invoke.assert_not_called()

    async def test_commit_fail(self, bot, ctx, msg):
        ctx.command_failed = True

        await bot.on_message(msg)
        ctx.session.commit.assert_not_called()

    async def test_commit_no_session(self, bot, ctx, msg):
        ctx.command_failed = False
        ctx.session.registry.has.return_value = False

        await bot.on_message(msg)
        ctx.session.registry.has.assert_called_once_with()
        ctx.session.commit.assert_not_called()

    async def test_commit_session(self, bot, ctx, msg):
        ctx.command_failed = False
        ctx.session.registry.has.return_value = True

        await bot.on_message(msg)
        ctx.session.registry.has.assert_called_once_with()
        ctx.session.commit.assert_called_once_with()


@mark.asyncio
async def test_on_command(bot, caplog, mocker):
    mock_msg = "Test message"
    format_message = mocker.patch("cardinal.bot.format_message", return_value=mock_msg)
    ctx = mocker.Mock()

    with caplog.at_level(logging.INFO, logger="cardinal.bot"):
        await bot.on_command(ctx)

    assert mock_msg in caplog.text
    format_message.assert_called_once_with(ctx.message)


@mark.asyncio
class TestOnCommandError:
    @fixture
    def clean_prefix(self, mocker):
        return mocker.patch("cardinal.bot.clean_prefix", return_value="Test prefix")

    @fixture
    def ctx(self, mocker):
        ctx = mocker.Mock()
        ctx.command.qualified_name = "Test command name"
        ctx.message.content = "Test message content"
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
        error_msg = (
            "Too few arguments. Did you forget anything?\n"
            f"See `{clean_prefix.return_value}help {ctx.command.qualified_name}` "
            "for information on the command."
        )
        ctx.send.assert_called_once_with(error_msg)

    async def test_bad_argument(self, bot, clean_prefix, ctx, mocker):
        error = mocker.Mock(spec=BadArgument)
        await bot.on_command_error(ctx, error)

        clean_prefix.assert_called_once_with(ctx)
        error_msg = (
            "Argument parsing failed. Did you mistype anything?\n"
            f"See `{clean_prefix.return_value}help {ctx.command.qualified_name}` "
            "for information on the command."
        )
        ctx.send.assert_called_once_with(error_msg)

    async def test_no_private_message(self, bot, clean_prefix, ctx, mocker):
        error = mocker.Mock(spec=NoPrivateMessage)
        await bot.on_command_error(ctx, error)

        clean_prefix.assert_not_called()
        error_msg = "Command cannot be used in private message channels."
        ctx.send.assert_called_once_with(error_msg)

    async def test_check_failure(self, bot, clean_prefix, ctx, mocker):
        error = mocker.MagicMock(spec=CheckFailure)
        await bot.on_command_error(ctx, error)

        clean_prefix.assert_not_called()
        error_msg = (
            "This command cannot be used in this context.\n"
            f"{error.__str__.return_value}"
        )
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

        with caplog.at_level(logging.ERROR, logger="cardinal.bot"):
            await bot.on_command_error(ctx, error)

        assert caplog.records != []
        clean_prefix.assert_not_called()
        error_msg = "An error occurred while executing the command."
        ctx.send.assert_called_once_with(error_msg)

    async def test_too_many_arguments(self, bot, clean_prefix, ctx, mocker):
        error = mocker.Mock(spec=TooManyArguments)
        await bot.on_command_error(ctx, error)

        clean_prefix.assert_called_once_with(ctx)
        error_msg = (
            "Too many arguments. Did you miss any quotes?\n"
            f"See `{clean_prefix.return_value}help {ctx.command.qualified_name}` "
            "for information on the command."
        )
        ctx.send.assert_called_once_with(error_msg)

    async def test_user_input_error(self, bot, clean_prefix, ctx, mocker):
        error = mocker.Mock(spec=UserInputError)
        await bot.on_command_error(ctx, error)

        clean_prefix.assert_called_once_with(ctx)
        error_msg = (
            f"\nSee `{clean_prefix.return_value}help {ctx.command.qualified_name}` "
            f"for information on the command."
        )
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
        error_msg = f"This command cannot be used in this context.\n{error.__str__.return_value}"
        ctx.send.assert_called_once_with(error_msg)

    async def test_missing_permissions(self, bot, clean_prefix, ctx, mocker):
        error = mocker.MagicMock(spec=MissingPermissions)
        await bot.on_command_error(ctx, error)

        clean_prefix.assert_not_called()
        error_msg = f"This command cannot be used in this context.\n{error.__str__.return_value}"
        ctx.send.assert_called_once_with(error_msg)

    async def test_bot_missing_permissions(self, bot, clean_prefix, ctx, mocker):
        error = mocker.MagicMock(spec=BotMissingPermissions)
        await bot.on_command_error(ctx, error)

        clean_prefix.assert_not_called()
        error_msg = f"This command cannot be used in this context.\n{error.__str__.return_value}"
        ctx.send.assert_called_once_with(error_msg)

    async def test_user_blacklisted(self, bot, clean_prefix, ctx, mocker):
        error = mocker.Mock(spec=UserBlacklisted)
        await bot.on_command_error(ctx, error)

        clean_prefix.assert_not_called()
        ctx.send.assert_not_called()


@mark.asyncio
async def test_on_error(bot, caplog):
    with caplog.at_level(logging.ERROR, logger="cardinal.bot"):
        await bot.on_error("Test name")

    assert caplog.records != []
