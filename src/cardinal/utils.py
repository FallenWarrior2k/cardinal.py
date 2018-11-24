def clean_prefix(ctx):
    user = ctx.me
    replacement = user.nick if ctx.guild and ctx.me.nick else user.name
    return ctx.prefix.replace(user.mention, '@' + replacement)


def format_message(msg):
    """
    Formats a :class:`discord.Message` for convenient output to e.g. loggers.

    :param msg: The message to format.
    :type msg: discord.Message
    :return: The formatted message as a string.
    :rtype: str
    """

    if msg.guild is None:
        return '[DM] {0.author.name} ({0.author.id}): {0.content}'.format(msg)
    else:
        return '[{0.guild.name} ({0.guild.id}) -> #{0.channel.name} ({0.channel.id})] ' \
               '{0.author.name} ({0.author.id}): {0.content}'.format(msg)


def _format_named_entity(obj):
    return '"{0.name}" ({0.id})'.format(obj)


def format_named_entities(*args):
    for arg in args:
        if hasattr(arg, 'name') and hasattr(arg, 'id'):
            yield _format_named_entity(arg)
