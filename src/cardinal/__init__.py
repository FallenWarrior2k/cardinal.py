import contextlib
import logging

import discord
import discord.ext.commands as _commands
from sqlalchemy.orm import sessionmaker

from . import errors, utils
from .db import create_all

logger = logging.getLogger(__name__)


# TODO: Implement server-specific prefixes
class Bot(_commands.Bot):
    async def before_invoke_hook(self, ctx: _commands.Context):
        ctx.session = self.sessionmaker()

    async def after_invoke_hook(self, ctx: _commands.Context):
        if ctx.command_failed:
            ctx.session.rollback()
        else:
            ctx.session.commit()

        ctx.session.close()

    def __init__(self, *args, default_game, engine, **kwargs):
        super().__init__(*args, **kwargs)
        self.default_game = default_game
        self.engine = engine
        _Session = sessionmaker()
        _Session.configure(bind=engine)
        self.sessionmaker = _Session
        self.before_invoke(self.before_invoke_hook)
        self.after_invoke(self.after_invoke_hook)

    @contextlib.contextmanager
    def session_scope(self):
        session = self.sessionmaker()

        try:
            yield session
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()

    async def on_ready(self):
        create_all(self.engine)
        logger.info('Logged into Discord as {}'.format(self.user))
        await self.change_presence(game=discord.Game(name=self.default_game))

    async def on_message(self, msg: discord.Message):
        ctx = await self.get_context(msg, cls=_commands.Context)
        if ctx.valid:
            await self.invoke(ctx)

    async def on_command(self, ctx: _commands.Context):
        logger.info(utils.format_message(ctx.message))

    async def on_command_completion(self, ctx: _commands.Context):
        pass  # Placeholder for future usage

    async def on_command_error(self, ctx: _commands.Context, ex: _commands.CommandError):
        error_msg = ''

        if isinstance(ex, _commands.NoPrivateMessage):
            error_msg = 'Command cannot be used in private message channels.'
        elif isinstance(ex, _commands.CheckFailure) and not isinstance(ex, errors.UserBlacklisted):
            error_msg = 'This command cannot be used in this context.\n'
            error_msg += str(ex)
        elif isinstance(ex, _commands.MissingRequiredArgument):
            error_msg = 'Too few arguments. Did you forget anything?'
        elif isinstance(ex, _commands.TooManyArguments):
            error_msg = 'Too many arguments. Did you miss any quotes?'
        elif isinstance(ex, _commands.BadArgument):
            error_msg = 'Argument parsing failed. Did you mistype anything?'
        elif isinstance(ex, _commands.CommandOnCooldown):
            error_msg = str(ex)

        if isinstance(ex, _commands.UserInputError):
            error_msg += '\nSee `{}help {}` for information on the command.' \
                .format(utils.clean_prefix(ctx), ctx.command.qualified_name)

        if isinstance(ex, _commands.CommandInvokeError):
            logger.error('An exception was raised while executing the command for "{}".'.format(ctx.message.content), exc_info=ex.original)
            error_msg += 'An error occurred while executing the command.'

        if error_msg != '':
            await ctx.send(error_msg)
