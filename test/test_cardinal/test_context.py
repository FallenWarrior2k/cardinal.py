import unittest as ut

from . import Empty
from cardinal.context import Context


class ContextTestCase(ut.TestCase):
    def test_ctor(self):
        bot = Empty()
        bot.session_scope = Empty()
        prefix = Empty()
        msg = Empty()
        msg._state = Empty()

        ctx = Context(bot=bot, prefix=prefix, message=msg)
        self.assertIs(ctx.bot, bot)
        self.assertIs(ctx.session_scope, bot.session_scope)
