import unittest as ut

from . import Empty
import cardinal.utils as utils


class EntityFormattingTestCase(ut.TestCase):
    def test_format_named_entity(self):
        obj = Empty()
        obj.name = 'Test obj'
        obj.id = 123456789
        expected = '"{0.name}" ({0.id})'.format(obj)
        got = utils.format_named_entity(obj)
        self.assertMultiLineEqual(expected, got)


class MessageFormattingTestCase(ut.TestCase):
    def setUp(self):
        msg = Empty()
        msg.content = 'Test message'
        msg.author = Empty()
        msg.author.name = 'Test author name'
        msg.author.id = 123456789
        msg.guild = None
        self.msg = msg

    def test_dm(self):
        expected = '[DM] {0.author.name} ({0.author.id}): {0.content}'.format(self.msg)
        got = utils.format_message(self.msg)
        self.assertMultiLineEqual(expected, got)

    def test_guild(self):
        self.msg.guild = Empty()
        self.msg.guild.name = 'Test guild'
        self.msg.guild.id = 987654321
        self.msg.channel = Empty()
        self.msg.channel.name = 'Test channel'
        self.msg.channel.id = 123459876

        expected = '[{0.guild.name} ({0.guild.id}) -> #{0.channel.name} ({0.channel.id})] {0.author.name} ({0.author.id}): {0.content}'.format(self.msg)
        got = utils.format_message(self.msg)
        self.assertMultiLineEqual(expected, got)


class CleanPrefixTestCase(ut.TestCase):
    def setUp(self):
        ctx = Empty()
        ctx.me = Empty()
        ctx.me.mention = '<@123456789>'
        ctx.me.name = 'Test bot'
        ctx.guild = None
        ctx.prefix = str()
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
