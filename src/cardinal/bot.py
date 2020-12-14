import sys
from contextvars import ContextVar
from logging import getLogger

from discord import Game, Intents
from discord.ext.commands import BadArgument
from discord.ext.commands import Bot as BaseBot
from discord.ext.commands import (
    CheckFailure, CommandError, CommandInvokeError, CommandOnCooldown,
    MissingRequiredArgument, NoPrivateMessage, TooManyArguments, UserInputError
)

from .errors import UserBlacklisted
from .utils import clean_prefix, format_message

event_context = ContextVar('event_context')
logger = getLogger(__name__)
intents = Intents.default()
intents.members = True


# TODO: Implement server-specific prefixes
class Bot(BaseBot):
    def __init__(
            self,
            *args,
            context_factory,
            default_game,
            scoped_session,
            **kwargs
    ):
        game = None
        if default_game:
            game = Game(name=default_game)

        super().__init__(*args, **kwargs, description='cardinal.py', game=game, intents=intents)

        self._context_factory = context_factory
        self._session = scoped_session
        self._event_counter = 0  # Dummy variable to have unique keys for `event_context`

    # Override to hook into event processing to manage event context
    async def _run_event(self, *args, **kwargs):
        # No need for copy_context because events run a new task anyway
        self._event_counter = (self._event_counter + 1) % sys.maxsize  # Cheap af "unique" ID system
        event_context.set(self._event_counter)

        try:
            await super()._run_event(*args, **kwargs)
        finally:
            self._session.remove()

    async def on_ready(self):
        logger.info(f'Logged into Discord as {self.user}')

    async def on_message(self, msg):
        if msg.author.bot:
            return

        ctx = await self.get_context(msg, cls=self._context_factory)
        await self.invoke(ctx)

        # Instead of calling `commit()` every time something touches the session, call it once here
        # Needs to happen here instead of e.g. a command_completion handler
        # due to the latter having their own context, i.e. a different session.
        if not ctx.command_failed and ctx.session.registry.has():
            ctx.session.commit()

    async def on_command(self, ctx):
        logger.info(format_message(ctx.message))

    async def on_command_error(self, ctx, ex: CommandError):
        error_msg = ''

        if isinstance(ex, NoPrivateMessage):
            error_msg = 'Command cannot be used in private message channels.'
        elif isinstance(ex, CheckFailure) and not isinstance(ex, UserBlacklisted):
            error_msg = f'This command cannot be used in this context.\n{ex}'
        elif isinstance(ex, MissingRequiredArgument):
            error_msg = 'Too few arguments. Did you forget anything?'
        elif isinstance(ex, TooManyArguments):
            error_msg = 'Too many arguments. Did you miss any quotes?'
        elif isinstance(ex, BadArgument):
            error_msg = 'Argument parsing failed. Did you mistype anything?'
        elif isinstance(ex, CommandOnCooldown):
            error_msg = str(ex)

        if isinstance(ex, UserInputError):
            error_msg += f'\nSee `{clean_prefix(ctx)}help {ctx.command.qualified_name}` ' \
                'for information on the command.'

        if isinstance(ex, CommandInvokeError):
            logger.error(
                f'An exception was raised while executing the command for "{ctx.message.content}".',
                exc_info=ex.original)
            error_msg += 'An error occurred while executing the command.'

        if error_msg != '':
            await ctx.send(error_msg)

    async def on_error(self, event, *args, **kwargs):
        logger.exception(f'An exception occured while handling event "{event}".')
