import logging

import discord

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
        channel = ctx.channel

        with session_scope() as session:
            return True if session.query(WhitelistedChannel).get(channel.id) or (callable(exception_predicate) and exception_predicate(ctx)) else False

    return check(predicate)


def format_message(msg):
    """
    Formats a :class:`discord.Message` for convenient output to e.g. loggers.

    :param msg: The message to format.
    :type msg: discord.Message
    :return: The formatted message as a string.
    :rtype: str
    """

    if msg.guild is None:
        return '[PM] {0.author.name} ({0.author.id}): {0.content}'.format(msg)
    else:
        return '[{0.guild.name} ({0.guild.id}) -> #{0.channel.name} ({0.channel.id})] {0.author.name} ({0.author.id}): {0.content}'.format(msg)


def format_discord_user(user: discord.User):
    return '"{0.name}" ({0.id})'.format(user)


def format_discord_guild(guild: discord.Guild):
    return '"{0.name}" ({0.id})'.format(guild)


def format_discord_channel(channel):
    return '"{0.name}" ({0.id})'.format(channel)
