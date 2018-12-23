import logging
from unittest import mock

import pytest
from discord import HTTPException

import cardinal.utils as utils
from cardinal.errors import PromptTimeout


class TestFormatMessage:
    @pytest.fixture
    def msg(self, mocker):
        msg = mocker.Mock()
        msg.content = 'Test message'
        msg.author.name = 'Test author name'
        msg.author.id = 123456789
        msg.guild = None
        return msg

    def test_dm(self, msg):
        expected = '[DM] {0.author.name} ({0.author.id}): {0.content}'.format(msg)
        got = utils.format_message(msg)
        assert expected == got

    def test_guild(self, mocker, msg):
        msg.guild = mocker.Mock()
        msg.guild.name = 'Test guild'
        msg.guild.id = 987654321
        msg.channel.name = 'Test channel'
        msg.channel.id = 123459876

        expected = '[{0.guild.name} ({0.guild.id}) -> #{0.channel.name} ({0.channel.id})] ' \
                   '{0.author.name} ({0.author.id}): {0.content}'.format(msg)
        got = utils.format_message(msg)
        assert expected == got


class TestCleanPrefix:
    @pytest.fixture
    def ctx(self, mocker):
        ctx = mocker.Mock()
        ctx.me.mention = '<@123456789>'
        ctx.me.name = 'Test bot'
        ctx.guild = None
        return ctx

    def test_regular_dm(self, ctx):
        ctx.prefix = '?'
        expected = '?'
        got = utils.clean_prefix(ctx)
        assert expected == got

    def test_mention_dm(self, ctx):
        ctx.prefix = ctx.me.mention
        expected = '@{}'.format(ctx.me.name)
        got = utils.clean_prefix(ctx)
        assert expected == got

    def test_regular_guild_no_nick(self, ctx):
        ctx.guild = True
        ctx.me.nick = None
        ctx.prefix = '?'
        expected = '?'
        got = utils.clean_prefix(ctx)
        assert expected == got

    def test_mention_guild_no_nick(self, ctx):
        ctx.guild = True
        ctx.me.nick = None
        ctx.prefix = ctx.me.mention
        expected = '@{}'.format(ctx.me.name)
        got = utils.clean_prefix(ctx)
        assert expected == got

    def test_regular_guild_nick(self, ctx):
        ctx.guild = True
        ctx.me.nick = 'Test nick'
        ctx.prefix = '?'
        expected = '?'
        got = utils.clean_prefix(ctx)
        assert expected == got

    def test_mention_guild_nick(self, ctx):
        ctx.guild = True
        ctx.me.nick = 'Test nick'
        ctx.prefix = ctx.me.mention
        expected = '@{}'.format(ctx.me.nick)
        got = utils.clean_prefix(ctx)
        assert expected == got


@pytest.mark.asyncio
class TestPrompt:
    @pytest.fixture
    def bot(self, mocker):
        bot = mocker.Mock()
        bot.wait_for = mocker.CoroMock()

        return bot

    @pytest.fixture
    def ctx(self, mocker, bot):
        ctx = mocker.Mock()
        ctx.bot = bot
        ctx.send = mocker.CoroMock()

        return ctx

    @pytest.fixture
    def msg(self, mocker):
        return mocker.Mock()

    async def test_response(self, ctx, mocker, msg):
        expected = mocker.Mock()
        ctx.bot.wait_for.coro.return_value = expected

        response = await utils.prompt(msg, ctx)
        assert response is expected

    async def test_default_timeout(self, ctx, msg):
        await utils.prompt(msg, ctx)

        assert ctx.bot.wait_for.call_count == 1

        args, kwargs = ctx.bot.wait_for.call_args
        assert args == ('message',)
        assert kwargs['timeout'] == 60.0

    async def test_custom_timeout(self, ctx, msg):
        await utils.prompt(msg, ctx, 1234)

        assert ctx.bot.wait_for.call_count == 1

        args, kwargs = ctx.bot.wait_for.call_args
        assert args == ('message',)
        assert kwargs['timeout'] == 1234

    async def test_pred(self, ctx, msg):
        await utils.prompt(msg, ctx)

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

    async def test_timeout_not_triggered(self, ctx, msg):
        await utils.prompt(msg, ctx)
        ctx.send.assert_called_once_with(msg)

    async def test_timeout_triggered(self, ctx, msg):
        ctx.bot.wait_for.coro.return_value = None

        with pytest.raises(PromptTimeout):
            await utils.prompt(msg, ctx)

        ctx.send.assert_called_once_with(msg)


@pytest.mark.asyncio
class TestMaybeSend:
    @pytest.fixture
    def target(self, mocker, request):
        kwargs = getattr(request, 'param', {})
        return_value = kwargs.get('return_value', mocker.DEFAULT)
        side_effect = kwargs.get('side_effect')

        target = mocker.MagicMock()

        target.kwargs = kwargs  # Convenience for lookup

        # Allow tests to make this raise an exception
        target.send = mocker.CoroMock(return_value=return_value, side_effect=side_effect)

        return target

    @pytest.fixture(params=[
        (), ('',), ('asdf', '1234')
    ])
    def args(self, request):
        return request.param

    @pytest.fixture(params=[
        {}, {'a': 'b'}, {'key': 'value', 'foo': 'bar'}
    ])
    def kwargs(self, request):
        return request.param

    @pytest.mark.parametrize(
        ['target'],
        [
            [{'return_value': mock.Mock()}]
        ],
        indirect=True
    )
    async def test_success(self, target, args, kwargs):
        msg = await utils.maybe_send(target, *args, **kwargs)

        target.send.assert_called_once_with(*args, **kwargs)
        assert msg is target.kwargs['return_value']

    @pytest.mark.parametrize(
        ['target', 'use_id'],
        [
            [{'side_effect': HTTPException(mock.MagicMock(), mock.MagicMock())}, True],
            [{'side_effect': HTTPException(mock.MagicMock(), mock.MagicMock())}, False]
        ],
        indirect=['target']
    )
    async def test_http_exception(self, caplog, target, args, kwargs, use_id):
        if use_id:
            target.id = 1234  # Ensure first execution path is selected
        else:
            del target.id  # Ensure second path is selected

        with caplog.at_level(logging.WARNING, logger='cardinal.utils'):
            msg = await utils.maybe_send(target, *args, **kwargs)

        assert msg is None
        assert caplog.records != []
