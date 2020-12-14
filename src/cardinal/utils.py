from asyncio import TimeoutError
from logging import getLogger

from discord import HTTPException

from .errors import PromptTimeout

logger = getLogger(__name__)


# TODO: Maybe make tests use an actual Context object instead of a mock
def clean_prefix(ctx):
    return ctx.prefix.replace(ctx.me.mention, '@' + ctx.me.display_name)


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
        timeout (typing.Union[float, int]): How long (in seconds) to wait for a response.
        Defaults to 60.

    Returns:
        discord.Message: Response sent by the user.

    Raises:
        cardinal.errors.PromptTimeout: No response by the user within the given timeframe.
    """
    def pred(m):
        return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id

    await ctx.send(msg)
    try:
        response = await ctx.bot.wait_for('message', check=pred, timeout=timeout)
    except TimeoutError as e:
        raise PromptTimeout() from e

    return response


async def maybe_send(target, *args, **kwargs):
    """
    Send a message to a given :class:`discord.abc.Messageable`, ignoring potential errors.

    Args:
        target (discord.abc.Messageable): Target to send to.
        *args, **kwargs: Passed through to send call.

    Returns:
        discord.Message: Newly created message object or None if failed.
    """
    try:
        return await target.send(*args, **kwargs)
    except HTTPException:
        if hasattr(target, 'id'):  # Target is channel or user
            channel = target
        else:  # Target is context instance
            channel = target.channel

        logger.warning(
            'Could not send message to {0} ({0.id}).'.format(channel),
            exc_info=True
        )
        return None
