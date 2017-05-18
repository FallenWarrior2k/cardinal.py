import logging
import discord
import discord.ext.commands as _discord
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

import __main__ as main

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__file__)
logger.setLevel(logging.INFO)

bot = _discord.Bot(command_prefix=main.config['cmd_prefix'], description='cardinal.py', formatter=_discord.HelpFormatter(show_check_failure=True))

engine = create_engine(main.config['db_connectstring'])
Base = declarative_base()
Session = sessionmaker()
Session.configure(bind=engine)


@bot.event
async def on_ready():
    try:
        logger.log(logging.INFO, 'Logged into Discord as {0}'.format(bot.user))
        await bot.change_presence(game=discord.Game(name=main.config['default_game']))
    except:
        pass


@bot.event
async def on_command_error(ex, ctx):
    error_msg = ''

    if isinstance(ex, _discord.errors.CheckFailure):
        error_msg = 'You are not allowed to use this command (here).'
    elif isinstance(ex, _discord.errors.MissingRequiredArgument):
        error_msg = 'Too few arguments.'
    elif isinstance(ex, _discord.errors.TooManyArguments):
        error_msg = 'Too many arguments.'
    elif isinstance(ex, _discord.errors.BadArgument):
        error_msg = 'Arguments parsing failed.'
    elif isinstance(ex, _discord.errors.NoPrivateMessage):
        error_msg = 'Command must not be used in private message channels.'
    elif isinstance(ex, _discord.errors.CommandOnCooldown):
        error_msg = str(ex)

    if isinstance(ex, _discord.errors.UserInputError):
        error_msg += ' See `{0.prefix}help {0.command}` for information on the command.'.format(ctx)

    if error_msg != '':
        await bot.send_message(ctx.message.channel, error_msg)

    if isinstance(ex, _discord.errors.CommandInvokeError):
        logger.log(logging.ERROR, ex.original)


@bot.event
async def on_command(cmd, ctx):
    if ctx.message.server is None:
        log_msg = '[PM] {user.name} ({user.id}): {message.content}'.format(user=ctx.message.author, message=ctx.message)
    else:
        log_msg = '[{0.server.name} ({0.server.id}) -> #{0.channel.name} ({0.channel.id})] {0.author.name} ({0.author.id}): {0.content}'.format(ctx.message)

    logger.log(logging.INFO, log_msg)

from cardinal.commands import *

bot.run(main.config['token'])