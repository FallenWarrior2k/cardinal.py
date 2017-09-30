import logging

import discord
import discord.ext.commands as commands

from ..commands import Cog
from ..context import Context
from ..db.whitelist import WhitelistedChannel
from ..utils import clean_prefix

logger = logging.getLogger(__name__)


class Whitelisting(Cog):
    def __init__(self, bot):
        super().__init__(bot)

    @commands.group()
    @commands.guild_only()
    async def whitelist(self, ctx: Context):
        """
        Whitelist channels to allow for command usage.

        Required context: Server
        """

        if ctx.invoked_subcommand is None:
            await ctx.send(
                'Invalid command passed. Possible choices are "add" and "remove".\n Please refer to `{}help {}` for further information.'
                .format(clean_prefix(ctx), ctx.invoked_with))
            return

    @whitelist.command()
    @commands.has_permissions(manage_channels=True)
    async def add(self, ctx: Context, *, channel: discord.TextChannel = None):
        """
        Add a channel to the whitelist.

        Required permissions:
            - Manage Channels

        Parameters:
            - [optional] channel: The channel to whitelist, identified by mention, ID, or name. Defaults to the current channel.
        """

        if channel is None:
            channel = ctx.channel

        with ctx.session_scope() as session:
            if session.query(WhitelistedChannel).get(channel.id):
                await ctx.send('Channel {} is already whitelisted.'.format(channel.mention))
                return

            db_channel = WhitelistedChannel(channel_id=channel.id, guild_id=channel.guild.id)
            session.add(db_channel)

        await ctx.send('Whitelisted channel {}.'.format(channel.mention))

    @whitelist.command()
    @commands.has_permissions(manage_channels=True)
    async def remove(self, ctx: Context, *, channel: discord.TextChannel = None):
        """
        Remove a channel from the whitelist.

        Required permissions:
            - Manage Channels

        Parameters:
            - [optional] channel: The channel to remove from the whitelist, identified by mention, ID, or name. Defaults to the current channel.
        """

        if channel is None:
            channel = ctx.channel

        with ctx.session_scope() as session:
            db_channel = session.query(WhitelistedChannel).get(channel.id)
            if not db_channel:
                await ctx.send('Channel {} is not whitelisted.'.format(channel.mention))
                return

            session.delete(db_channel)
        await ctx.send('Removed channel {} from whitelist.'.format(channel.mention))

    @whitelist.command('list')
    async def _list(self, ctx: Context):
        """
        Enumerate whitelisted channels on the current server.
        """

        answer = 'Whitelisted channels on this server:```\n'

        channel_list = []

        with ctx.session_scope() as session:
            for db_channel in session.query(WhitelistedChannel).filter_by(guild_id=ctx.guild.id):
                channel = discord.utils.get(ctx.guild.text_channels, id=db_channel.channel_id)
                if not channel:
                    session.delete(db_channel)
                    continue

                channel_list.append(channel)

        channel_list.sort(key=lambda c: c.position)

        for channel in channel_list:
            answer += '#'
            answer += channel.name
            answer += '\n'

        answer += '```'
        await ctx.send(answer)
