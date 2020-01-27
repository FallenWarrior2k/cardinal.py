from discord.ext import commands

from .context import Context
from .db import WhitelistedChannel
from .errors import ChannelNotWhitelisted


def channel_whitelisted(exception_predicate=None):
    """
    Decorator that marks a channel as required to be whitelisted by a previous command.
    Takes an optional predicate,
    that checks whether or not an exception should be made for the current context.
    Args:
        exception_predicate (typing.Callable): A predicate taking a context as its only argument,
        returning a boolean value.

    Returns:
        typing.Callable: Decorator to use on discord.py commands.
    """

    def predicate(ctx: Context):
        # Manually create session as ctx.session is not created until after checks have succeeded
        with ctx.bot.session_scope() as session:
            db_channel = session.query(WhitelistedChannel).get(ctx.channel.id)

        if not (db_channel or (callable(exception_predicate) and exception_predicate(ctx))):
            raise ChannelNotWhitelisted(ctx)

        return True

    return commands.check(predicate)
