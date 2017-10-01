import unittest as ut

from . import Empty
import cardinal.errors as errors


class ChannelNotWhitelistedTestCase(ut.TestCase):
    def test_ctor(self):
        ctx = Empty()
        ctx.channel = Empty()
        ctx.channel.mention = '<#123456789>'
        ex = errors.ChannelNotWhitelisted(ctx)
        expected = 'Channel {} is not whitelisted.'.format(ctx.channel.mention)
        got = str(ex)
        self.assertMultiLineEqual(expected, got)
        self.assertIs(ctx.channel, ex.channel)


class UserBlacklistedTestCase(ut.TestCase):
    def test_ctor(self):
        ctx = Empty()
        ctx.author = Empty()
        ex = errors.UserBlacklisted(ctx)
        self.assertIs(ctx.author, ex.user)
