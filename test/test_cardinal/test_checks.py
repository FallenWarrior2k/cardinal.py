import contextlib
import unittest as ut

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from test_cardinal import Empty
from cardinal.checks import channel_whitelisted
from cardinal.db import Base
from cardinal.db.whitelist import WhitelistedChannel
from cardinal.errors import ChannelNotWhitelisted


class ChannelWhitelistedTestCase(ut.TestCase):

    # Hooks
    def setUp(self):
        engine = create_engine('sqlite:///')
        _Session = sessionmaker()
        _Session.configure(bind=engine)
        Base.metadata.create_all(engine)

        @contextlib.contextmanager
        def session_scope():
            session = _Session()

            try:
                yield session
                session.commit()
            except:
                session.rollback()
                raise
            finally:
                session.close()

        ctx = Empty()
        ctx.session_scope = session_scope
        ctx.channel = Empty()
        ctx.channel.id = 123456789
        ctx.channel.mention = '<#123456789>'
        self.ctx = ctx

    # Helpers
    def expect_fail(self, obj):
        pred = obj.__commands_checks__[0]
        with self.assertRaises(ChannelNotWhitelisted) as cm:
            pred(self.ctx)

        exc = cm.exception
        self.assertIs(self.ctx.channel, exc.channel)

    def expect_success(self, obj):
        pred = obj.__commands_checks__[0]
        self.assertTrue(pred(self.ctx))

    def whitelist_channel(self):
        with self.ctx.session_scope() as session:
            session.add(WhitelistedChannel(channel_id=self.ctx.channel.id))

    # Tests
    def test_not_whitelisted_no_predicate(self):
        obj = (channel_whitelisted())(Empty())
        self.expect_fail(obj)

    def test_not_whitelisted_uncallable_predicate(self):
        obj = (channel_whitelisted(Empty()))(Empty())
        self.expect_fail(obj)

    def test_not_whitelisted_predicate_no_exception(self):
        obj = (channel_whitelisted(lambda ctx: False))(Empty())
        self.expect_fail(obj)

    def test_not_whitelisted_predicate_exception(self):
        obj = (channel_whitelisted(lambda ctx: True))(Empty())
        self.expect_success(obj)

    def test_whitelisted_no_predicate(self):
        self.whitelist_channel()
        obj = (channel_whitelisted())(Empty())
        self.expect_success(obj)

    def test_whitelisted_uncallable_predicate(self):
        self.whitelist_channel()
        obj = (channel_whitelisted(Empty()))(Empty())
        self.expect_success(obj)

    def test_whitelisted_predicate_no_exception(self):
        self.whitelist_channel()
        obj = (channel_whitelisted(lambda ctx: False))(Empty())
        self.expect_success(obj)

    def test_whitelisted_predicate_exception(self):
        self.whitelist_channel()
        obj = (channel_whitelisted(lambda ctx: True))(Empty())
        self.expect_success(obj)
