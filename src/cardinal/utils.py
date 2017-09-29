import logging

import discord

logger = logging.getLogger(__name__)


def clean_prefix(ctx):
    user = ctx.me
    return ctx.prefix.replace(user.mention, '@' + user.name)


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


def format_named_entity(obj):
    return '"{0.name}" ({0.id})'.format(obj)
