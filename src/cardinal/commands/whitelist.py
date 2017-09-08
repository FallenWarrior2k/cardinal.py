import discord
import discord.ext.commands as commands

from cardinal.commands import Cog
from cardinal.db import session_scope
from cardinal.db.whitelist import WhitelistedChannel
from cardinal.utils import clean_prefix


class Whitelisting(Cog):
    def __init__(self, bot):
        super().__init__(bot)

    @commands.group()
    @commands.guild_only()
    async def whitelist(self, ctx: commands.Context):
        """
        Provides functionality for whitelisting channels to allow usage of channel-restricted commands.

        Required context: Server

        Required permissions:
            - Manage Channels
        """

        if ctx.invoked_subcommand is None:
            await ctx.send(
                'Invalid command passed. Possible choices are "add" and "remove".\n Please refer to `{}help {}` for further information.'
                .format(clean_prefix(ctx), ctx.invoked_with))
            return

    @whitelist.command()
    @commands.has_permissions(manage_channels=True)
    async def add(self, ctx: commands.Context, *, channel: discord.TextChannel = None):
        """
        Whitelist a channel.

        Parameters:
            - [optional] channel: The channel to whitelist, identified by mention, ID, or name. Defaults to the current channel.
        """

        if channel is None:
            channel = ctx.channel

        with session_scope() as session:
            if session.query(WhitelistedChannel).get(channel.id):
                await ctx.send('Channel {} is already whitelisted.'.format(channel.mention))
                return

            channel_db = WhitelistedChannel(channel_id=channel.id, guild_id=channel.guild.id)
            session.add(channel_db)

        await ctx.send('Whitelisted channel {}.'.format(channel.mention))

    @whitelist.command()
    @commands.has_permissions(manage_channels=True)
    async def remove(self, ctx: commands.Context, *, channel: discord.TextChannel = None):
        """
        Remove a channel from the whitelist.

        Parameters:
            - [optional] channel: The channel to remove from the whitelist, identified by mention, ID, or name. Defaults to the current channel.
        """

        if channel is None:
            channel = ctx.channel

        with session_scope() as session:
            channel_db = session.query(WhitelistedChannel).get(channel.id)
            if not channel_db:
                await ctx.send('Channel {} is not whitelisted.'.format(channel.mention))
                return

            session.delete(channel_db)
        await ctx.send('Removed channel {} from whitelist.'.format(channel.mention))

    @whitelist.command('list')
    async def _list(self, ctx: commands.Context):
        """
        Enumerate whitelisted channels on the current guild.
        """
        pass  # TODO
