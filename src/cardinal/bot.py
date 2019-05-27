import contextlib
import logging

from discord import Game, Intents
from discord.ext.commands import BadArgument
from discord.ext.commands import Bot as BaseBot
from discord.ext.commands import (
    CheckFailure, CommandError, CommandInvokeError, CommandOnCooldown,
    MissingRequiredArgument, NoPrivateMessage, TooManyArguments, UserInputError
)
from lazy import lazy
from sqlalchemy.orm import sessionmaker

from .context import Context
from .errors import UserBlacklisted
from .utils import clean_prefix, format_message

logger = logging.getLogger(__name__)
intents = Intents.default()
intents.members = True


# TODO: Implement server-specific prefixes
class Bot(BaseBot):
    async def before_invoke_hook(self, ctx: Context):
        ctx.session_allowed = True

    async def after_invoke_hook(self, ctx: Context):
        if not ctx.session_used:
            return

        if ctx.command_failed:
            ctx.session.rollback()
        else:
            ctx.session.commit()

        session = ctx.session  # Local reference to close after it gets deleted from Context object
        ctx.session_allowed = False
        lazy.invalidate(ctx, 'session')  # Ensure nothing tries to use the session after closing it
        session.close()

    def __init__(self, *args, engine, default_game=None, **kwargs):
        game = None
        if default_game:
            game = Game(name=default_game)

        super().__init__(*args, **kwargs, description='cardinal.py', game=game, intents=intents)

        self.sessionmaker = sessionmaker(bind=engine)
        self.before_invoke(self.before_invoke_hook)
        self.after_invoke(self.after_invoke_hook)

    @contextlib.contextmanager
    def session_scope(self):
        session = self.sessionmaker()

        try:
            yield session
            session.commit()
        except BaseException:
            session.rollback()
            raise
        finally:
            session.close()

    async def on_ready(self):
        logger.info('Logged into Discord as {}'.format(self.user))

    async def on_message(self, msg):
        if msg.author.bot:
            return

        ctx = await self.get_context(msg, cls=Context)
        await self.invoke(ctx)

    async def on_command(self, ctx: Context):
        logger.info(format_message(ctx.message))

    async def on_command_error(self, ctx: Context, ex: CommandError):
        error_msg = ''

        if isinstance(ex, NoPrivateMessage):
            error_msg = 'Command cannot be used in private message channels.'
        elif isinstance(ex, CheckFailure) and not isinstance(ex, UserBlacklisted):
            error_msg = 'This command cannot be used in this context.\n'
            error_msg += str(ex)
        elif isinstance(ex, MissingRequiredArgument):
            error_msg = 'Too few arguments. Did you forget anything?'
        elif isinstance(ex, TooManyArguments):
            error_msg = 'Too many arguments. Did you miss any quotes?'
        elif isinstance(ex, BadArgument):
            error_msg = 'Argument parsing failed. Did you mistype anything?'
        elif isinstance(ex, CommandOnCooldown):
            error_msg = str(ex)

        if isinstance(ex, UserInputError):
            error_msg += '\nSee `{}help {}` for information on the command.' \
                .format(clean_prefix(ctx), ctx.command.qualified_name)

        if isinstance(ex, CommandInvokeError):
            logger.error(
                'An exception was raised while executing the command for "{}".'
                .format(ctx.message.content), exc_info=ex.original)
            error_msg += 'An error occurred while executing the command.'

        if error_msg != '':
            await ctx.send(error_msg)

    async def on_error(self, event, *args, **kwargs):
        logger.exception('An exception occured while handling event "{}".'.format(event))
