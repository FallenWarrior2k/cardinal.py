import logging
import discord
import discord.ext.commands as commands

import cardinal.utils as utils
from __main__ import config

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# TODO: Implement server-specific prefixes
bot = commands.Bot(command_prefix=commands.when_mentioned_or(config['cmd_prefix']), description='cardinal.py')


@bot.event
async def on_ready():
    logger.log(logging.INFO, 'Logged into Discord as {0}'.format(bot.user))
    await bot.change_presence(game=discord.Game(name=config['default_game']))


@bot.event
async def on_command_error(ex, ctx):
    error_msg = ''

    if isinstance(ex, commands.errors.CheckFailure):
        error_msg = 'You are not allowed to use this command (here).'
    elif isinstance(ex, commands.errors.MissingRequiredArgument):
        error_msg = 'Too few arguments.'
    elif isinstance(ex, commands.errors.TooManyArguments):
        error_msg = 'Too many arguments.'
    elif isinstance(ex, commands.errors.BadArgument):
        error_msg = 'Arguments parsing failed.'
    elif isinstance(ex, commands.errors.NoPrivateMessage):
        error_msg = 'Command must not be used in private message channels.'
    elif isinstance(ex, commands.errors.CommandOnCooldown):
        error_msg = str(ex)

    if isinstance(ex, commands.errors.UserInputError):
        error_msg += ' See `{}help {}` for information on the command.'\
            .format(utils.clean_prefix(ctx), ctx.command.qualified_name)

    if error_msg != '':
        await bot.send_message(ctx.message.channel, error_msg)

    if isinstance(ex, commands.errors.CommandInvokeError):
        logger.log(logging.ERROR, utils.format_exception(ex.original))


@bot.event
async def on_command(cmd, ctx):
    logger.log(logging.INFO, utils.format_message(ctx.message))
