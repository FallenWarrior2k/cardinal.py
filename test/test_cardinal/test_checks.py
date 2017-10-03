import contextlib
import unittest as ut
import unittest.mock as mock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

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

        ctx = mock.Mock()
        ctx.session_scope = session_scope
        ctx.channel.id = 123456789
        ctx.channel.mention = '<#123456789>'
        self.ctx = ctx
        self.command = mock.Mock()

    # Helpers
    def expect_fail(self, command):
        pred = command.__commands_checks__[0]
        with self.assertRaises(ChannelNotWhitelisted) as cm:
            pred(self.ctx)

        exc = cm.exception
        self.assertIs(self.ctx.channel, exc.channel)

    def expect_success(self, command):
        pred = command.__commands_checks__[0]
        self.assertTrue(pred(self.ctx))

    def whitelist_channel(self):
        with self.ctx.session_scope() as session:
            session.add(WhitelistedChannel(channel_id=self.ctx.channel.id))

    # Tests
    def test_not_whitelisted_no_predicate(self):
        wrapped_command = (channel_whitelisted())(self.command)
        self.expect_fail(wrapped_command)

    def test_not_whitelisted_uncallable_predicate(self):
        exc_pred = mock.NonCallableMock()
        wrapped_command = (channel_whitelisted(exc_pred))(self.command)
        self.expect_fail(wrapped_command)

    def test_not_whitelisted_predicate_no_exception(self):
        exc_pred = mock.Mock(return_value=False)
        wrapped_command = (channel_whitelisted(exc_pred))(self.command)
        self.expect_fail(wrapped_command)
        exc_pred.assert_called_once_with(self.ctx)

    def test_not_whitelisted_predicate_exception(self):
        exc_pred = mock.Mock(return_value=True)
        wrapped_command = (channel_whitelisted(exc_pred))(self.command)
        self.expect_success(wrapped_command)
        exc_pred.assert_called_once_with(self.ctx)

    def test_whitelisted_no_predicate(self):
        self.whitelist_channel()
        wrapped_command = (channel_whitelisted())(self.command)
        self.expect_success(wrapped_command)

    def test_whitelisted_uncallable_predicate(self):
        self.whitelist_channel()
        exc_pred = mock.NonCallableMock()
        wrapped_command = (channel_whitelisted(exc_pred))(self.command)
        self.expect_success(wrapped_command)

    def test_whitelisted_predicate_no_exception(self):
        self.whitelist_channel()
        exc_pred = mock.Mock(return_value=False)
        obj = (channel_whitelisted(exc_pred))(self.command)
        self.expect_success(obj)
        exc_pred.assert_not_called()

    def test_whitelisted_predicate_exception(self):
        self.whitelist_channel()
        exc_pred = mock.Mock(return_value=True)
        obj = (channel_whitelisted(exc_pred))(self.command)
        self.expect_success(obj)
        exc_pred.assert_not_called()
