import logging
import unittest as ut
import unittest.mock as mock
from asyncio import get_event_loop

from discord.ext import commands
from sqlalchemy.orm import Session, sessionmaker

from . import CoroMock
from cardinal.bot import Bot
from cardinal.errors import UserBlacklisted

default_game = 'Test game'
engine = mock.NonCallableMock()
bot = Bot(default_game=default_game, engine=engine, command_prefix='Test prefix')
loop = get_event_loop()


def tearDownModule():
    loop.run_until_complete(bot.close())
    loop.close()


class BotCtorTestCase(ut.TestCase):
    def test(self):
        self.assertIs(bot.engine, engine)
        self.assertIsInstance(bot.sessionmaker, sessionmaker)


@mock.patch.object(bot, 'sessionmaker', side_effect=lambda: mock.NonCallableMock(spec=Session))
class BotBeforeInvokeHookTestCase(ut.TestCase):
    def test(self, sessionmaker):
        ctx = mock.NonCallableMock()

        loop.run_until_complete(bot.before_invoke_hook(ctx))

        sessionmaker.assert_called_once_with()
        self.assertIsInstance(ctx.session, Session)


class BotAfterInvokeHookTestCase(ut.TestCase):
    def setUp(self):
        ctx = mock.NonCallableMock()
        ctx.session = mock.NonCallableMock(spec=Session)
        self.ctx = ctx

    def test_failed(self):
        self.ctx.command_failed = True
        loop.run_until_complete(bot.after_invoke_hook(self.ctx))

        self.ctx.session.rollback.assert_called_once_with()
        self.ctx.session.close.assert_called_once_with()

    def test_success(self):
        self.ctx.command_failed = False
        loop.run_until_complete(bot.after_invoke_hook(self.ctx))

        self.ctx.session.commit.assert_called_once_with()
        self.ctx.session.close.assert_called_once_with()


@mock.patch.object(bot, 'sessionmaker', side_effect=lambda: mock.NonCallableMock(spec=Session))
class BotSessionScopeTestCase(ut.TestCase):
    def test_no_exception(self, sessionmaker):
        with bot.session_scope() as session:
            self.assertIsInstance(session, Session)

        sessionmaker.assert_called_once_with()
        session.commit.assert_called_once_with()
        session.close.assert_called_once_with()

    def test_exception(self, sessionmaker):
        exc_message = 'Test exception message'
        exc = Exception(exc_message)
        with self.assertRaises(Exception, msg=exc_message):
            with bot.session_scope() as session:
                self.assertIsInstance(session, Session)
                raise exc

        sessionmaker.assert_called_once_with()
        session.rollback.assert_called_once_with()
        session.close.assert_called_once_with()


class BotOnReadyTestCase(ut.TestCase):
    def test(self):
        with self.assertLogs('cardinal.bot'):
            loop.run_until_complete(bot.on_ready())


@mock.patch('cardinal.bot.format_message', return_value='Test message')
class BotOnCommandTestCase(ut.TestCase):
    def test(self, format_message):
        ctx = mock.NonCallableMock()
        with self.assertLogs('cardinal.bot') as log:
            loop.run_until_complete(bot.on_command(ctx))

        self.assertMultiLineEqual(log.output[0], 'INFO:cardinal.bot:Test message')
        format_message.assert_called_once_with(ctx.message)


@mock.patch('cardinal.bot.clean_prefix', return_value='Test prefix')
class BotOnCommandErrorTestCase(ut.TestCase):
    def setUp(self):
        ctx = mock.NonCallableMock()
        ctx.command.qualified_name = 'Test command name'
        ctx.message.content = 'Test message content'

        output = []
        ctx.send = CoroMock(side_effect=output.append)
        self.ctx = ctx
        self.output = output

    def test_command_error(self, clean_prefix):
        error = mock.NonCallableMock(spec=commands.CommandError)
        loop.run_until_complete(bot.on_command_error(self.ctx, error))

        clean_prefix.assert_not_called()
        self.ctx.send.assert_not_called()

    def test_missing_required_argument(self, clean_prefix):
        error = mock.NonCallableMock(spec=commands.MissingRequiredArgument)
        loop.run_until_complete(bot.on_command_error(self.ctx, error))

        clean_prefix.assert_called_once_with(self.ctx)
        error_msg = 'Too few arguments. Did you forget anything?\n' \
                    'See `{}help {}` for information on the command.'\
                    .format(clean_prefix.return_value, self.ctx.command.qualified_name)
        self.ctx.send.assert_called_once_with(error_msg)
        self.assertIn(error_msg, self.output)

    def test_bad_argument(self, clean_prefix):
        error = mock.NonCallableMock(spec=commands.BadArgument)
        loop.run_until_complete(bot.on_command_error(self.ctx, error))

        clean_prefix.assert_called_once_with(self.ctx)
        error_msg = 'Argument parsing failed. Did you mistype anything?\n' \
                    'See `{}help {}` for information on the command.'\
                    .format(clean_prefix.return_value, self.ctx.command.qualified_name)
        self.ctx.send.assert_called_once_with(error_msg)
        self.assertIn(error_msg, self.output)

    def test_no_private_message(self, clean_prefix):
        error = mock.NonCallableMock(spec=commands.NoPrivateMessage)
        loop.run_until_complete(bot.on_command_error(self.ctx, error))

        clean_prefix.assert_not_called()
        error_msg = 'Command cannot be used in private message channels.'\
            .format(clean_prefix.return_value, self.ctx.command.qualified_name)
        self.ctx.send.assert_called_once_with(error_msg)
        self.assertIn(error_msg, self.output)

    def test_check_failure(self, clean_prefix):
        error = mock.NonCallableMagicMock(spec=commands.CheckFailure)
        loop.run_until_complete(bot.on_command_error(self.ctx, error))

        clean_prefix.assert_not_called()
        error_msg = 'This command cannot be used in this context.\n' \
                    '{}'.format(error.__str__.return_value)
        self.ctx.send.assert_called_once_with(error_msg)
        self.assertIn(error_msg, self.output)

    def test_command_not_found(self, clean_prefix):
        error = mock.NonCallableMock(spec=commands.CommandNotFound)
        loop.run_until_complete(bot.on_command_error(self.ctx, error))

        clean_prefix.assert_not_called()
        self.ctx.send.assert_not_called()

    def test_disabled_command(self, clean_prefix):
        error = mock.NonCallableMock(spec=commands.DisabledCommand)
        loop.run_until_complete(bot.on_command_error(self.ctx, error))

        clean_prefix.assert_not_called()
        self.ctx.send.assert_not_called()

    def test_command_invoke_error(self, clean_prefix):
        error = mock.NonCallableMock(spec=commands.CommandInvokeError)
        error.original = mock.NonCallableMagicMock()

        with self.assertLogs('cardinal.bot', logging.ERROR):
            loop.run_until_complete(bot.on_command_error(self.ctx, error))

        clean_prefix.assert_not_called()
        error_msg = 'An error occurred while executing the command.'
        self.ctx.send.assert_called_once_with(error_msg)
        self.assertIn(error_msg, self.output)

    def test_too_many_arguments(self, clean_prefix):
        error = mock.NonCallableMock(spec=commands.TooManyArguments)
        loop.run_until_complete(bot.on_command_error(self.ctx, error))

        clean_prefix.assert_called_once_with(self.ctx)
        error_msg = 'Too many arguments. Did you miss any quotes?\n' \
                    'See `{}help {}` for information on the command.'\
                    .format(clean_prefix.return_value, self.ctx.command.qualified_name)
        self.ctx.send.assert_called_once_with(error_msg)
        self.assertIn(error_msg, self.output)

    def test_user_input_error(self, clean_prefix):
        error = mock.NonCallableMock(spec=commands.UserInputError)
        loop.run_until_complete(bot.on_command_error(self.ctx, error))

        clean_prefix.assert_called_once_with(self.ctx)
        error_msg = '\nSee `{}help {}` for information on the command.' \
            .format(clean_prefix.return_value, self.ctx.command.qualified_name)
        self.ctx.send.assert_called_once_with(error_msg)
        self.assertIn(error_msg, self.output)

    def test_command_on_cooldown(self, clean_prefix):
        error = mock.NonCallableMagicMock(spec=commands.CommandOnCooldown)
        loop.run_until_complete(bot.on_command_error(self.ctx, error))

        clean_prefix.assert_not_called()
        error_msg = error.__str__.return_value
        self.ctx.send.assert_called_once_with(error_msg)
        self.assertIn(error_msg, self.output)

    def test_not_owner(self, clean_prefix):
        error = mock.NonCallableMagicMock(spec=commands.NotOwner)
        loop.run_until_complete(bot.on_command_error(self.ctx, error))

        clean_prefix.assert_not_called()
        error_msg = 'This command cannot be used in this context.\n{}'\
                    .format(error.__str__.return_value)
        self.ctx.send.assert_called_once_with(error_msg)
        self.assertIn(error_msg, self.output)

    def test_missing_permissions(self, clean_prefix):
        error = mock.NonCallableMagicMock(spec=commands.MissingPermissions)
        loop.run_until_complete(bot.on_command_error(self.ctx, error))

        clean_prefix.assert_not_called()
        error_msg = 'This command cannot be used in this context.\n{}'\
                    .format(error.__str__.return_value)
        self.ctx.send.assert_called_once_with(error_msg)
        self.assertIn(error_msg, self.output)

    def test_bot_missing_permissions(self, clean_prefix):
        error = mock.NonCallableMagicMock(spec=commands.BotMissingPermissions)
        loop.run_until_complete(bot.on_command_error(self.ctx, error))

        clean_prefix.assert_not_called()
        error_msg = 'This command cannot be used in this context.\n{}'\
                    .format(error.__str__.return_value)
        self.ctx.send.assert_called_once_with(error_msg)
        self.assertIn(error_msg, self.output)

    def test_user_blacklisted(self, clean_prefix):
        error = mock.NonCallableMock(spec=UserBlacklisted)
        loop.run_until_complete(bot.on_command_error(self.ctx, error))

        clean_prefix.assert_not_called()
        self.ctx.send.assert_not_called()


class BotOnErrorTestCase(ut.TestCase):
    def test(self):
        name = 'Test name'

        with self.assertLogs('cardinal.bot', logging.ERROR):
            loop.run_until_complete(bot.on_error(name))
