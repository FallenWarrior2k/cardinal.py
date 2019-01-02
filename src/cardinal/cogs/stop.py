from logging import getLogger

from discord.ext.commands import bot_has_permissions, group, guild_only, has_permissions

from ..utils import maybe_send
from .basecog import BaseCog

logger = getLogger(__name__)


class Stop(BaseCog):
    """
    Utilities for locking down chat channels.
    """

    def __init__(self, bot):
        super().__init__(bot)
        self.perm_cache = {}

    @group()
    @guild_only()
    @has_permissions(manage_channels=True)
    @bot_has_permissions(manage_channels=True)
    async def stop(self, ctx):
        """
        Commands to (un)restrict access to a channel.

        Required context: Server

        Required permissions:
            - Manage Channels

        Required bot permissions:
            - Manage Channels
        """
        if ctx.invoked_subcommand is None:
            await maybe_send(ctx, 'Invalid subcommand passed. Possible options are "on" and "off".')

    @stop.command()
    async def on(self, ctx):
        """
        Restrict messaging to a channel for everyone.
        Note that the user issueing this command should probably have some form of way to
        still write to the channel, or they will need to release the lock manually.
        """
        channel = ctx.channel

        await maybe_send(ctx, 'Sending messages to this channel has been restricted.')

        overwrite = channel.overwrites_for(ctx.guild.default_role)
        self.perm_cache.setdefault(channel.id, overwrite.send_messages)
        overwrite.send_messages = False
        await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)

    @stop.command()
    async def off(self, ctx):
        """
        Re-open a channel after it was locked down.
        This restores the default role's permission to send messages to this channel
        to its previous value.
        If the channel was not previously locked down, that permission is set to the global default.
        """
        channel = ctx.channel

        overwrite = channel.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = self.perm_cache.pop(channel.id, None)
        overwrite = overwrite if not overwrite.is_empty() else None  # Clear overwrite if empty
        await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)

        await maybe_send(ctx, 'Sending messages to this channel has been unrestricted.')
