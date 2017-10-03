import unittest as ut
import unittest.mock as mock

from cardinal.context import Context


class ContextTestCase(ut.TestCase):
    def test_ctor(self):
        bot = mock.NonCallableMock()
        prefix = mock.NonCallableMock()
        msg = mock.NonCallableMock()

        ctx = Context(bot=bot, prefix=prefix, message=msg)
        self.assertIs(ctx.bot, bot)
        self.assertIs(ctx.session_scope, bot.session_scope)
