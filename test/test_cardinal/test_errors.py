import unittest as ut

from . import Empty
import cardinal.errors as errors


class ChannelNotWhitelistedTestCase(ut.TestCase):
    def setUp(self):
        ctx = Empty()
        ctx.channel = Empty()
        ctx.channel.mention = '<#123456789>'
        self.ctx = ctx

    def test_ctor(self):
        ex = errors.ChannelNotWhitelisted(self.ctx)
        expected = 'Channel {} is not whitelisted.'.format(self.ctx.channel.mention)
        got = str(ex)
        self.assertMultiLineEqual(expected, got)
        self.assertIs(self.ctx.channel, ex.channel)


class UserBlacklistedTestCase(ut.TestCase):
    def setUp(self):
        ctx = Empty()
        ctx.author = Empty()
        self.ctx = ctx

    def test_ctor(self):
        ex = errors.UserBlacklisted(self.ctx)
        self.assertIs(self.ctx.author, ex.user)
