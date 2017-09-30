from discord.ext.commands import check

from .context import Context
from .db.whitelist import WhitelistedChannel
from .errors import ChannelNotWhitelisted


def channel_whitelisted(exception_predicate=None):
    """
    Decorator that marks a channel as required to be whitelisted by a previous command.
    Takes an optional :param:`exception_predicate`, that checks whether or not an exception should be made for the current context.

    :param exception_predicate: A predicate taking a context as its only argument, returning a boolean value.
    :type exception_predicate: callable
    """

    def predicate(ctx: Context):
        channel = ctx.channel

        with ctx.session_scope() as session:
            if not (session.query(WhitelistedChannel).get(channel.id) or (callable(exception_predicate) and exception_predicate(ctx))):
                raise ChannelNotWhitelisted(ctx)

            return True

    return check(predicate)