import unittest as ut
import unittest.mock as mock
from asyncio import new_event_loop

import pytest

import cardinal.utils as utils

from . import CoroMock


class FormatMessageTestCase(ut.TestCase):
    def setUp(self):
        msg = mock.NonCallableMock()
        msg.content = 'Test message'
        msg.author.name = 'Test author name'
        msg.author.id = 123456789
        msg.guild = None
        self.msg = msg

    def test_dm(self):
        expected = '[DM] {0.author.name} ({0.author.id}): {0.content}'.format(self.msg)
        got = utils.format_message(self.msg)
        self.assertMultiLineEqual(expected, got)

    def test_guild(self):
        self.msg.guild = mock.NonCallableMock()
        self.msg.guild.name = 'Test guild'
        self.msg.guild.id = 987654321
        self.msg.channel.name = 'Test channel'
        self.msg.channel.id = 123459876

        expected = '[{0.guild.name} ({0.guild.id}) -> #{0.channel.name} ({0.channel.id})] {0.author.name} ({0.author.id}): {0.content}'.format(self.msg)
        got = utils.format_message(self.msg)
        self.assertMultiLineEqual(expected, got)


class CleanPrefixTestCase(ut.TestCase):
    def setUp(self):
        ctx = mock.NonCallableMock()
        ctx.me.mention = '<@123456789>'
        ctx.me.name = 'Test bot'
        ctx.guild = None
        self.ctx = ctx

    def test_regular_dm(self):
        self.ctx.prefix = '?'
        expected = '?'
        got = utils.clean_prefix(self.ctx)
        self.assertMultiLineEqual(expected, got)

    def test_mention_dm(self):
        self.ctx.prefix = self.ctx.me.mention
        expected = '@{}'.format(self.ctx.me.name)
        got = utils.clean_prefix(self.ctx)
        self.assertMultiLineEqual(expected, got)

    def test_regular_guild_no_nick(self):
        self.ctx.guild = True
        self.ctx.me.nick = None
        self.ctx.prefix = '?'
        expected = '?'
        got = utils.clean_prefix(self.ctx)
        self.assertMultiLineEqual(expected, got)

    def test_mention_guild_no_nick(self):
        self.ctx.guild = True
        self.ctx.me.nick = None
        self.ctx.prefix = self.ctx.me.mention
        expected = '@{}'.format(self.ctx.me.name)
        got = utils.clean_prefix(self.ctx)
        self.assertMultiLineEqual(expected, got)

    def test_regular_guild_nick(self):
        self.ctx.guild = True
        self.ctx.me.nick = 'Test nick'
        self.ctx.prefix = '?'
        expected = '?'
        got = utils.clean_prefix(self.ctx)
        self.assertMultiLineEqual(expected, got)

    def test_mention_guild_nick(self):
        self.ctx.guild = True
        self.ctx.me.nick = 'Test nick'
        self.ctx.prefix = self.ctx.me.mention
        expected = '@{}'.format(self.ctx.me.nick)
        got = utils.clean_prefix(self.ctx)
        self.assertMultiLineEqual(expected, got)


class TestPrompt:
    @pytest.fixture
    def loop(self):
        return new_event_loop()

    @pytest.fixture
    def bot(self, mocker):
        _bot = mocker.Mock()
        _bot.wait_for = CoroMock()

        return _bot

    @pytest.fixture
    def ctx(self, mocker, bot):
        ctx = mocker.Mock()
        ctx.bot = bot
        ctx.send = CoroMock()

        return ctx

    @pytest.fixture
    def msg(self, mocker):
        return mocker.Mock()

    def test_response(self, ctx, loop, mocker, msg):
        expected = mocker.Mock()
        ctx.bot.wait_for.coro.return_value = expected

        response = loop.run_until_complete(utils.prompt(msg, ctx))
        assert response is expected

    def test_default_timeout(self, ctx, loop, msg):
        loop.run_until_complete(utils.prompt(msg, ctx))

        assert ctx.bot.wait_for.call_count == 1

        args, kwargs = ctx.bot.wait_for.call_args
        assert args == ('message',)
        assert kwargs['timeout'] == 60.0

    def test_custom_timeout(self, ctx, loop, msg):
        loop.run_until_complete(utils.prompt(msg, ctx, 1234))

        assert ctx.bot.wait_for.call_count == 1

        args, kwargs = ctx.bot.wait_for.call_args
        assert args == ('message',)
        assert kwargs['timeout'] == 1234

    def test_pred(self, ctx, loop, msg):
        loop.run_until_complete(utils.prompt(msg, ctx))

        *_, kwargs = ctx.bot.wait_for.call_args
        pred = kwargs['check']
        assert callable(pred)

        # Two conditions => four possible combinations
        # False, False
        msg.author.id = 1
        ctx.author.id = 2
        msg.channel.id = 3
        ctx.channel.id = 4
        assert not pred(msg)

        # False, True
        ctx.channel.id = 3
        assert not pred(msg)

        # True, False
        ctx.channel.id = 4
        ctx.author.id = 1
        assert not pred(msg)

        # True, True
        ctx.channel.id = 3
        assert pred(msg)

    def test_timeout_not_triggered(self, ctx, loop, msg):
        loop.run_until_complete(utils.prompt(msg, ctx))
        ctx.send.assert_called_once_with(msg)

    def test_timeout_triggered(self, ctx, loop, msg):
        ctx.bot.wait_for.coro.return_value = None

        loop.run_until_complete(utils.prompt(msg, ctx))

        assert ctx.send.call_count == 2
        assert ctx.send.call_args_list[0] == ((msg,), {})
        assert ctx.send.call_args_list[1] == (('Terminating process due to timeout.',), {})
