import unittest as ut
import unittest.mock as mock

import cardinal.errors as errors


class ChannelNotWhitelistedCtorTestCase(ut.TestCase):
    def test(self):
        ctx = mock.NonCallableMock()
        ctx.channel.mention = '<#123456789>'
        ex = errors.ChannelNotWhitelisted(ctx)
        expected = 'Channel {} is not whitelisted.'.format(ctx.channel.mention)
        got = str(ex)
        self.assertMultiLineEqual(expected, got)
        self.assertIs(ctx.channel, ex.channel)


class UserBlacklistedCtorTestCase(ut.TestCase):
    def test(self):
        ctx = mock.NonCallableMock()
        ex = errors.UserBlacklisted(ctx)
        self.assertIs(ctx.author, ex.user)
