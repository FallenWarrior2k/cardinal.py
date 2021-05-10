from asyncio import gather
from collections import namedtuple
from logging import getLogger

from discord.ext.commands import (
    Cog,
    bot_has_permissions,
    group,
    guild_only,
    has_permissions,
)

from ..utils import maybe_send

logger = getLogger(__name__)
_perms = namedtuple("perms", ["send_messages", "add_reactions"])


def is_public(channel):
    """
    Tests if a given text channel is public.

    Args:
        channel (discord.TextChannel: Channel to check.

    Returns:
        bool: `True` when the channel is public, `False` otherwise.
    """
    role = channel.guild.default_role
    return channel.overwrites_for(role).read_messages is not False


class Stop(Cog):
    """
    Utilities for locking down text channels.
    """

    def __init__(self):
        self._perm_cache = {}

    async def _lock_channel(self, channel):
        """
        Locks a text channel, denying Send Messages and Add Reactions.

        Args:
            channel (discord.TextChannel): Channel to lock.
        """
        role = channel.guild.default_role

        await maybe_send(
            channel, "Sending messages to this channel has been restricted."
        )

        overwrite = channel.overwrites_for(role)
        self._perm_cache.setdefault(
            channel.id, _perms(overwrite.send_messages, overwrite.add_reactions)
        )
        overwrite.send_messages = False
        overwrite.add_reactions = False
        await channel.set_permissions(role, overwrite=overwrite)

    async def _unlock_channel(self, channel):
        """
        Unlock a text channel, restoring Send Messages and
        Add Reactions to their previous values.

        Args:
            channel (discord.TextChannel): Channel to unlock.
        """
        role = channel.guild.default_role
        overwrite = channel.overwrites_for(role)

        perms = self._perm_cache.pop(channel.id, _perms(None, None))
        overwrite.send_messages = perms.send_messages
        overwrite.add_reactions = perms.add_reactions

        overwrite = (
            overwrite if not overwrite.is_empty() else None
        )  # Clear overwrite if empty
        await channel.set_permissions(role, overwrite=overwrite)

        await maybe_send(
            channel, "Sending messages to this channel has been unrestricted."
        )

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
            await maybe_send(
                ctx, 'Invalid subcommand passed. Possible options are "on" and "off".'
            )

    @stop.command("on")
    async def _on_single(self, ctx):
        """
        Restrict messaging and reactions to a channel for everyone.
        Note that the user issueing this command should probably have some form of way to
        still write to the channel, or they will need to release the lock manually.
        """
        channel = ctx.channel
        await self._lock_channel(channel)

    @stop.command("off")
    async def _off_single(self, ctx):
        """
        Re-open a channel after it was locked down.
        This restores the default role's modified permissions,
        i.e. Send Messages and Add Reactions, to their previous values.
        If the channel was not previously locked down, nothing happens.
        """
        channel = ctx.channel

        await self._unlock_channel(channel)

    @stop.group()
    async def all(self, ctx):
        """
        Commands for (un)locking all public channels at once.
        """
        if ctx.invoked_subcommand is None:
            await maybe_send(
                ctx, 'Invalid subcommand passed. Possible options are "on" and "off".'
            )

    @all.command("on")
    async def _on_all(self, ctx):
        """
        Works like regular "stop on", except it locks all
        public channels instead of just the current one.
        """
        # Public channel => @everyone is not denied read perms
        coros = (
            self._lock_channel(channel)
            for channel in ctx.guild.text_channels
            if is_public(channel)
        )
        await gather(*coros)

    @all.command("off")
    async def _off_all(self, ctx):
        """
        Works like regular "stop off", except that it unlocks all
        locked public channels at once.
        """
        public_channels = {
            channel.id: channel
            for channel in ctx.guild.text_channels
            if is_public(channel)
        }
        # Select all locked channels in current guild using set intersection
        locked_channel_ids = self._perm_cache.keys() & public_channels.keys()

        coros = (
            self._unlock_channel(public_channels[channel_id])
            for channel_id in locked_channel_ids
        )
        await gather(*coros)
