import logging

from discord.ext.commands import check

from cardinal.db import session_scope
from cardinal.db.whitelist import WhitelistedChannel

logger = logging.getLogger(__name__)


def clean_prefix(ctx):
    user = ctx.bot.user
    return ctx.prefix.replace(user.mention, '@' + user.name)


def channel_whitelisted(exception_predicate=None):
    """
    Decorator that marks a channel as required to be whitelisted by a previous command.
    Takes an optional :param:`exception_predicate`, that checks whether or not an exception should be made for the current context.

    :param exception_predicate: A predicate taking a context as its only argument, returning a boolean value.
    :type exception_predicate: callable
    """

    def predicate(ctx):
        channel_obj = ctx.message.channel

        with session_scope() as session:
            channel_db = session.query(WhitelistedChannel).get(channel_obj.id)

        if channel_db or (callable(exception_predicate) and exception_predicate(ctx)):
            return True
        else:
            return False

    return check(predicate)


def format_exception(e):
    """
    Formats an :class:`Exception` for convenient output to e.g. loggers.

    :param e: The exception to format.
    :type e: Exception
    :return: The formatted exception as a string.
    :rtype: str
    """
    return '{}: {}'.format(type(e).__name__, e)


def format_message(msg):
    """
    Formats a :class:`discord.Message` for convenient output to e.g. loggers.

    :param msg: The message to format.
    :type msg: discord.Message
    :return: The formatted message as a string.
    :rtype: str
    """

    if msg.server is None:
        return '[PM] {0.author.name} ({0.author.id}): {0.content}'.format(msg)
    else:
        return '[{0.server.name} ({0.server.id}) -> #{0.channel.name} ({0.channel.id})] {0.author.name} ({0.author.id}): {0.content}'.format(
            msg)
