import logging
import unittest as ut
import unittest.mock as mock
from asyncio import get_event_loop

import discord
import discord.ext.commands as commands
from sqlalchemy.orm import Session

from . import CoroMock
from cardinal import Bot, errors

default_game = 'Test game'
engine = mock.NonCallableMock()
bot = Bot(default_game=default_game, engine=engine, command_prefix='Test prefix')
loop = get_event_loop()


def tearDownModule():
    loop.run_until_complete(bot.close())
    loop.close()


class BotCtorTestCase(ut.TestCase):
    def test(self):
        self.assertIs(bot.default_game, default_game)
        self.assertIs(bot.engine, engine)


class BotSessionScopeTestCase(ut.TestCase):
    @mock.patch.object(bot, 'sessionmaker', return_value=mock.NonCallableMock(spec=Session))
    def test_no_exception(self, sessionmaker):
        with bot.session_scope() as session:
            self.assertIsInstance(session, Session)

        sessionmaker.assert_called_once_with()
        sessionmaker.return_value.commit.assert_called_once_with()
        sessionmaker.return_value.close.assert_called_once_with()

    @mock.patch.object(bot, 'sessionmaker', return_value=mock.NonCallableMock(spec=Session))
    def test_exception(self, sessionmaker):
        exc_message = 'Test exception message'
        exc = Exception(exc_message)
        with self.assertRaises(Exception, msg=exc_message):
            with bot.session_scope() as session:
                self.assertIsInstance(session, Session)
                raise exc

        sessionmaker.assert_called_once_with()
        sessionmaker.return_value.rollback.assert_called_once_with()
        sessionmaker.return_value.close.assert_called_once_with()


@mock.patch.object(commands.Bot, 'user', new_callable=mock.PropertyMock, return_value='Test user#1234')
@mock.patch.object(commands.Bot, 'change_presence', new_callable=CoroMock)
@mock.patch('cardinal.create_all')
class BotOnReadyTestCase(ut.TestCase):
    def test(self, create_all, change_presence, user):
        with self.assertLogs('cardinal') as log:
            loop.run_until_complete(bot.on_ready())

        self.assertMultiLineEqual(log.output[0], 'INFO:cardinal:Logged into Discord as {}'.format(user.return_value))
        create_all.assert_called_once_with(bot.engine)
        change_presence.assert_called_once_with(game=discord.Game(name=bot.default_game))


@mock.patch.object(commands.Bot, 'invoke', new_callable=CoroMock)
@mock.patch('cardinal.context.Context')
@mock.patch.object(commands.Bot, 'get_context', new_callable=CoroMock)
class BotOnMessageTestCase(ut.TestCase):
    def test_invalid(self, get_context, context, invoke):
        get_context.coro.return_value = mock.NonCallableMock(valid=False)
        msg = mock.NonCallableMock()
        loop.run_until_complete(bot.on_message(msg))
        get_context.assert_called_once_with(msg, cls=context)
        invoke.assert_not_called()

    def test_valid(self, get_context, context, invoke):
        get_context.coro.return_value = mock.NonCallableMock(valid=True)
        msg = mock.NonCallableMock()
        loop.run_until_complete(bot.on_message(msg))
        get_context.assert_called_once_with(msg, cls=context)
        invoke.assert_called_once_with(get_context.coro.return_value)


@mock.patch('cardinal.utils.format_message', return_value='Test message')
class BotOnCommandTestCase(ut.TestCase):
    def test(self, format_message):
        ctx = mock.NonCallableMock()
        with self.assertLogs('cardinal') as log:
            loop.run_until_complete(bot.on_command(ctx))

        self.assertMultiLineEqual(log.output[0], 'INFO:cardinal:Test message')
        format_message.assert_called_once_with(ctx.message)


class BotOnCommandCompletionTestCase(ut.TestCase):
    def test(self):
        ctx = mock.NonCallableMock()
        loop.run_until_complete(bot.on_command_completion(ctx))


@mock.patch('cardinal.utils.clean_prefix', return_value='Test prefix')
@mock.patch('cardinal.logger', autospec=True)
class BotOnCommandErrorTestCase(ut.TestCase):
    def setUp(self):
        ctx = mock.NonCallableMock()
        ctx.command.qualified_name = 'Test command name'
        ctx.message.content = 'Test message content'

        output = []
        ctx.send = CoroMock(side_effect=output.append)
        self.ctx = ctx
        self.output = output

    def test_command_error(self, logger, clean_prefix):
        error = mock.NonCallableMock(spec=commands.CommandError)
        loop.run_until_complete(bot.on_command_error(self.ctx, error))

        logger.error.assert_not_called()
        clean_prefix.assert_not_called()
        self.ctx.send.assert_not_called()

    def test_missing_required_argument(self, logger, clean_prefix):
        error = mock.NonCallableMock(spec=commands.MissingRequiredArgument)
        loop.run_until_complete(bot.on_command_error(self.ctx, error))

        logger.error.assert_not_called()
        clean_prefix.assert_called_once_with(self.ctx)
        error_msg = 'Too few arguments. Did you forget anything?\nSee `{}help {}` for information on the command.'\
            .format(clean_prefix.return_value, self.ctx.command.qualified_name)
        self.ctx.send.assert_called_once_with(error_msg)
        self.assertIn(error_msg, self.output)

    def test_bad_argument(self, logger, clean_prefix):
        error = mock.NonCallableMock(spec=commands.BadArgument)
        loop.run_until_complete(bot.on_command_error(self.ctx, error))

        logger.error.assert_not_called()
        clean_prefix.assert_called_once_with(self.ctx)
        error_msg = 'Argument parsing failed. Did you mistype anything?\nSee `{}help {}` for information on the command.'\
            .format(clean_prefix.return_value, self.ctx.command.qualified_name)
        self.ctx.send.assert_called_once_with(error_msg)
        self.assertIn(error_msg, self.output)

    def test_no_private_message(self, logger, clean_prefix):
        error = mock.NonCallableMock(spec=commands.NoPrivateMessage)
        loop.run_until_complete(bot.on_command_error(self.ctx, error))

        logger.error.assert_not_called()
        clean_prefix.assert_not_called()
        error_msg = 'Command cannot be used in private message channels.'\
            .format(clean_prefix.return_value, self.ctx.command.qualified_name)
        self.ctx.send.assert_called_once_with(error_msg)
        self.assertIn(error_msg, self.output)

    def test_check_failure(self, logger, clean_prefix):
        error = mock.NonCallableMagicMock(spec=commands.CheckFailure)
        loop.run_until_complete(bot.on_command_error(self.ctx, error))

        logger.error.assert_not_called()
        clean_prefix.assert_not_called()
        error_msg = 'This command cannot be used in this context.\n{}'.format(error.__str__.return_value)
        self.ctx.send.assert_called_once_with(error_msg)
        self.assertIn(error_msg, self.output)

    def test_command_not_found(self, logger, clean_prefix):
        error = mock.NonCallableMock(spec=commands.CommandNotFound)
        loop.run_until_complete(bot.on_command_error(self.ctx, error))

        logger.error.assert_not_called()
        clean_prefix.assert_not_called()
        self.ctx.send.assert_not_called()

    def test_disabled_command(self, logger, clean_prefix):
        error = mock.NonCallableMock(spec=commands.DisabledCommand)
        loop.run_until_complete(bot.on_command_error(self.ctx, error))

        logger.error.assert_not_called()
        clean_prefix.assert_not_called()
        self.ctx.send.assert_not_called()

    def test_command_invoke_error(self, logger, clean_prefix):
        error = mock.NonCallableMock(spec=commands.CommandInvokeError)
        error.original = mock.NonCallableMagicMock()
        logger.error = logging.getLogger('cardinal').error

        with self.assertLogs('cardinal', logging.ERROR):
            loop.run_until_complete(bot.on_command_error(self.ctx, error))

        clean_prefix.assert_not_called()
        error_msg = 'An error occurred while executing the command.'
        self.ctx.send.assert_called_once_with(error_msg)
        self.assertIn(error_msg, self.output)

    def test_too_many_arguments(self, logger, clean_prefix):
        error = mock.NonCallableMock(spec=commands.TooManyArguments)
        loop.run_until_complete(bot.on_command_error(self.ctx, error))

        logger.error.assert_not_called()
        clean_prefix.assert_called_once_with(self.ctx)
        error_msg = 'Too many arguments. Did you miss any quotes?\nSee `{}help {}` for information on the command.'\
            .format(clean_prefix.return_value, self.ctx.command.qualified_name)
        self.ctx.send.assert_called_once_with(error_msg)
        self.assertIn(error_msg, self.output)

    def test_user_input_error(self, logger, clean_prefix):
        error = mock.NonCallableMock(spec=commands.UserInputError)
        loop.run_until_complete(bot.on_command_error(self.ctx, error))

        logger.error.assert_not_called()
        clean_prefix.assert_called_once_with(self.ctx)
        error_msg = '\nSee `{}help {}` for information on the command.' \
            .format(clean_prefix.return_value, self.ctx.command.qualified_name)
        self.ctx.send.assert_called_once_with(error_msg)
        self.assertIn(error_msg, self.output)

    def test_command_on_cooldown(self, logger, clean_prefix):
        error = mock.NonCallableMagicMock(spec=commands.CommandOnCooldown)
        loop.run_until_complete(bot.on_command_error(self.ctx, error))

        logger.error.assert_not_called()
        clean_prefix.assert_not_called()
        error_msg = error.__str__.return_value
        self.ctx.send.assert_called_once_with(error_msg)
        self.assertIn(error_msg, self.output)

    def test_not_owner(self, logger, clean_prefix):
        error = mock.NonCallableMagicMock(spec=commands.NotOwner)
        loop.run_until_complete(bot.on_command_error(self.ctx, error))

        logger.error.assert_not_called()
        clean_prefix.assert_not_called()
        error_msg = 'This command cannot be used in this context.\n{}'.format(error.__str__.return_value)
        self.ctx.send.assert_called_once_with(error_msg)
        self.assertIn(error_msg, self.output)

    def test_missing_permissions(self, logger, clean_prefix):
        error = mock.NonCallableMagicMock(spec=commands.MissingPermissions)
        loop.run_until_complete(bot.on_command_error(self.ctx, error))

        logger.error.assert_not_called()
        clean_prefix.assert_not_called()
        error_msg = 'This command cannot be used in this context.\n{}'.format(error.__str__.return_value)
        self.ctx.send.assert_called_once_with(error_msg)
        self.assertIn(error_msg, self.output)

    def test_bot_missing_permissions(self, logger, clean_prefix):
        error = mock.NonCallableMagicMock(spec=commands.BotMissingPermissions)
        loop.run_until_complete(bot.on_command_error(self.ctx, error))

        logger.error.assert_not_called()
        clean_prefix.assert_not_called()
        error_msg = 'This command cannot be used in this context.\n{}'.format(error.__str__.return_value)
        self.ctx.send.assert_called_once_with(error_msg)
        self.assertIn(error_msg, self.output)

    def test_user_blacklisted(self, logger, clean_prefix):
        error = mock.NonCallableMock(spec=errors.UserBlacklisted)
        loop.run_until_complete(bot.on_command_error(self.ctx, error))

        logger.error.assert_not_called()
        clean_prefix.assert_not_called()
        self.ctx.send.assert_not_called()
