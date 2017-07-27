import logging

import discord
import discord.ext.commands as _commands

import cardinal.utils as utils
from __main__ import config

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# TODO: Implement server-specific prefixes
bot = _commands.Bot(command_prefix=config['cmd_prefix'], description='cardinal.py')


@bot.event
async def on_ready():
    logger.log(logging.INFO, 'Logged into Discord as {0}'.format(bot.user))
    try:
        await bot.change_presence(game=discord.Game(name=config['default_game']))
    except KeyError:
        pass


@bot.event
async def on_command_error(ex, ctx):
    error_msg = ''

    if isinstance(ex, _commands.CheckFailure):
        error_msg = 'This command cannot be used in this context.'
    elif isinstance(ex, _commands.MissingRequiredArgument):
        error_msg = 'Too few arguments.'
    elif isinstance(ex, _commands.TooManyArguments):
        error_msg = 'Too many arguments.'
    elif isinstance(ex, _commands.BadArgument):
        error_msg = 'Arguments parsing failed.'
    elif isinstance(ex, _commands.NoPrivateMessage):
        error_msg = 'Command must not be used in private message channels.'
    elif isinstance(ex, _commands.CommandOnCooldown):
        error_msg = str(ex)

    if isinstance(ex, _commands.UserInputError):
        error_msg += ' See `{}help {}` for information on the command.' \
            .format(utils.clean_prefix(ctx), ctx.command.qualified_name)

    if error_msg != '':
        await bot.send_message(ctx.message.channel, error_msg)

    if isinstance(ex, _commands.CommandInvokeError):
        logger.log(logging.ERROR, utils.format_exception(ex.original))


@bot.event
async def on_command(cmd, ctx):
    logger.log(logging.INFO, utils.format_message(ctx.message))
