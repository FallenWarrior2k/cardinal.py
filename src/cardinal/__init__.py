import logging

import discord
import discord.ext.commands as _commands

import cardinal.utils as utils
import cardinal.errors as errors

logger = logging.getLogger(__name__)


# TODO: Implement server-specific prefixes
class Bot(_commands.Bot):
    def __init__(self, *args, default_game, **kwargs):
        self.default_game = default_game
        super().__init__(*args, **kwargs)

    async def on_ready(self):
        logger.info('Logged into Discord as {}'.format(self.user))
        try:
            await self.change_presence(game=discord.Game(name=self.default_game))
        except KeyError:
            pass

    async def on_message(self, msg: discord.Message):
        ctx = await self.get_context(msg, cls=_commands.Context)  # TODO: Make own context with dict to store data between commands
        if ctx.valid:
            await self.invoke(ctx)

    async def on_command(self, ctx: _commands.Context):
        logger.info(utils.format_message(ctx.message))

    async def on_command_completion(self, ctx: _commands.Context):
        pass  # Placeholder for future usage

    async def on_command_error(self, ctx: _commands.Context, ex: _commands.CommandError):
        error_msg = ''

        if isinstance(ex, _commands.CheckFailure) and not isinstance(ex, errors.UserBlacklisted):
            error_msg = 'This command cannot be used in this context.\n'
            error_msg += str(ex)
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
            error_msg += '\nSee `{}help {}` for information on the command.' \
                .format(utils.clean_prefix(ctx), ctx.command.qualified_name)

        if isinstance(ex, _commands.CommandInvokeError):
            logger.error('An exception was raised while executing the command for "{}".'.format(ctx.message.content), exc_info=ex.original)
            error_msg += 'An error occurred while executing the command.'

        if error_msg != '':
            await ctx.send(error_msg)
