import logging

from discord.ext.commands import check

import cardinal
import cardinal.db
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

        dbsession = cardinal.db.Session()
        channel_db = dbsession.query(WhitelistedChannel).get(channel_obj.id)

        if channel_db or exception_predicate(ctx):
            return True
        else:
            return False

    return check(predicate)