import unittest as ut
import unittest.mock as mock
from asyncio import get_event_loop

import discord
import discord.ext.commands as commands

from . import CoroMock
from cardinal import Bot

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
@mock.patch.object(commands.Bot, 'get_context', new_callable=CoroMock)
class BotOnMessageTestCase(ut.TestCase):
    pass


@mock.patch('cardinal.utils.format_message', return_value='Test message')
class BotOnCommandTestCase(ut.TestCase):
    def test(self, format_message):
        ctx = mock.NonCallableMock()
        with self.assertLogs('cardinal') as log:
            loop.run_until_complete(bot.on_command(ctx))

        self.assertMultiLineEqual(log.output[0], 'INFO:cardinal:Test message')
        format_message.assert_called_once_with(ctx.message)


@mock.patch('cardinal.utils.clean_prefix')
class BotOnCommandErrorTestCase(ut.TestCase):
    pass
