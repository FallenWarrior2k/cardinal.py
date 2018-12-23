from .errors import PromptTimeout


def clean_prefix(ctx):
    user = ctx.me
    replacement = user.nick if ctx.guild and ctx.me.nick else user.name
    return ctx.prefix.replace(user.mention, '@' + replacement)


def format_message(msg):
    """
    Format a :class:`discord.Message` for convenient output to e.g. loggers.

    Args:
        msg (discord.Message): Message to format.

    Returns:
        str: Input message formatted as a string.
    """

    if msg.guild is None:
        return '[DM] {0.author.name} ({0.author.id}): {0.content}'.format(msg)
    else:
        return '[{0.guild.name} ({0.guild.id}) -> #{0.channel.name} ({0.channel.id})] ' \
               '{0.author.name} ({0.author.id}): {0.content}'.format(msg)


async def prompt(msg, ctx, timeout=60.0):
    """
    Prompt a user with a given message

    Args:
        msg (str): Prompt to display to the user.
        ctx (cardinal.context.Context): Context that holds the channel and the user to listen for.
        timeout (typings.Union[float, int]): How long (in seconds) to wait for a response.
        Defaults to 60.

    Returns:
        discord.Message: Response sent by the user.

    Raises:
        cardinal.errors.PromptTimeout: No response by the user within the given timeframe.
    """
    def pred(m):
        return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id

    await ctx.send(msg)
    response = await ctx.bot.wait_for('message', check=pred, timeout=timeout)
    if not response:
        raise PromptTimeout()

    return response
