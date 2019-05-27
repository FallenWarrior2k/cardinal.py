from pytest import fixture, raises
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from cardinal.checks import channel_whitelisted
from cardinal.db import Base
from cardinal.db.whitelist import WhitelistedChannel
from cardinal.errors import ChannelNotWhitelisted


class TestChannelWhitelisted:
    @fixture(scope='class')
    def engine(self):
        # TODO: Clean up this god-forsaken mess
        engine = create_engine('sqlite:///')
        Base.metadata.create_all(engine)
        return engine

    @fixture
    def session(self, engine):
        session = Session(bind=engine)
        yield session
        session.rollback()
        session.close()

    @fixture
    def ctx(self, mocker, session):
        ctx = mocker.Mock()
        ctx.bot.session_scope.return_value = mocker.MagicMock()
        ctx.bot.session_scope.return_value.__enter__.return_value = session
        ctx.channel.id = 123456789
        ctx.channel.mention = '<#123456789>'

        return ctx

    @fixture
    def command(self, mocker):
        return mocker.Mock()

    # Helpers
    @staticmethod
    def expect_fail(command, ctx):
        pred = command.__commands_checks__[0]
        with raises(ChannelNotWhitelisted) as exc_info:
            pred(ctx)

        exc = exc_info.value
        assert ctx.channel is exc.channel

    @staticmethod
    def expect_success(command, ctx):
        pred = command.__commands_checks__[0]
        assert pred(ctx)

    @staticmethod
    def whitelist_channel(session, ctx):
        session.add(WhitelistedChannel(channel_id=ctx.channel.id))

    # Tests
    def test_not_whitelisted_no_predicate(self, command, ctx):
        wrapped_command = (channel_whitelisted())(command)
        self.expect_fail(wrapped_command, ctx)

    def test_not_whitelisted_uncallable_predicate(self, command, ctx, mocker):
        exc_pred = mocker.NonCallableMock()
        wrapped_command = (channel_whitelisted(exc_pred))(command)
        self.expect_fail(wrapped_command, ctx)

    def test_not_whitelisted_predicate_no_exception(self, command, ctx, mocker):
        exc_pred = mocker.Mock(return_value=False)
        wrapped_command = (channel_whitelisted(exc_pred))(command)
        self.expect_fail(wrapped_command, ctx)
        exc_pred.assert_called_once_with(ctx)

    def test_not_whitelisted_predicate_exception(self, command, ctx, mocker):
        exc_pred = mocker.Mock(return_value=True)
        wrapped_command = (channel_whitelisted(exc_pred))(command)
        self.expect_success(wrapped_command, ctx)
        exc_pred.assert_called_once_with(ctx)

    def test_whitelisted_no_predicate(self, command, ctx, session):
        self.whitelist_channel(session, ctx)
        wrapped_command = (channel_whitelisted())(command)
        self.expect_success(wrapped_command, ctx)

    def test_whitelisted_uncallable_predicate(self, command, ctx, mocker, session):
        self.whitelist_channel(session, ctx)
        exc_pred = mocker.NonCallableMock()
        wrapped_command = (channel_whitelisted(exc_pred))(command)
        self.expect_success(wrapped_command, ctx)

    def test_whitelisted_predicate_no_exception(self, command, ctx, mocker, session):
        self.whitelist_channel(session, ctx)
        exc_pred = mocker.Mock(return_value=False)
        wrapped_command = (channel_whitelisted(exc_pred))(command)
        self.expect_success(wrapped_command, ctx)
        exc_pred.assert_not_called()

    def test_whitelisted_predicate_exception(self, command, ctx, mocker, session):
        self.whitelist_channel(session, ctx)
        exc_pred = mocker.Mock(return_value=True)
        wrapped_command = (channel_whitelisted(exc_pred))(command)
        self.expect_success(wrapped_command, ctx)
        exc_pred.assert_not_called()
