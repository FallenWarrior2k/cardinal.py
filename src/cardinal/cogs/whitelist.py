import logging

import discord
from discord.ext import commands

from ..db import WhitelistedChannel
from ..utils import clean_prefix, format_named_entities
from .basecog import BaseCog

logger = logging.getLogger(__name__)


class Whitelisting(BaseCog):
    @commands.group()
    @commands.guild_only()
    async def whitelist(self, ctx: commands.Context):
        """
        Whitelist channels to allow for command usage.

        Required context: Server
        """

        if ctx.invoked_subcommand is None:
            await ctx.send(
                'Invalid command passed. Possible choices are "add" and "remove".\n'
                'Please refer to `{}help {}` for further information.'
                .format(clean_prefix(ctx), ctx.invoked_with))
            return

    @whitelist.command()
    @commands.has_permissions(manage_channels=True)
    async def add(self, ctx: commands.Context, *, channel: discord.TextChannel = None):
        """
        Add a channel to the whitelist.

        Required permissions:
            - Manage Channels

        Parameters:
            - [optional] channel: The channel to whitelist, identified by mention, ID, or name.
            Defaults to the current channel.
        """

        if channel is None:
            channel = ctx.channel

        if ctx.session.query(WhitelistedChannel).get(channel.id):
            await ctx.send('Channel {} is already whitelisted.'.format(channel.mention))
            return

        db_channel = WhitelistedChannel(channel_id=channel.id, guild_id=channel.guild.id)
        ctx.session.add(db_channel)

        logger.info('Added channel {} on guild {} to whitelist.'
                    .format(*format_named_entities(channel, ctx.guild)))
        await ctx.send('Whitelisted channel {}.'.format(channel.mention))

    @whitelist.command()
    @commands.has_permissions(manage_channels=True)
    async def remove(self, ctx: commands.Context, *, channel: discord.TextChannel = None):
        """
        Remove a channel from the whitelist.

        Required permissions:
            - Manage Channels

        Parameters:
            - [optional] channel: The channel to remove from the whitelist,
            identified by mention, ID, or name.
            Defaults to the current channel.
        """

        if not channel:
            channel = ctx.channel

        db_channel = ctx.session.query(WhitelistedChannel).get(channel.id)
        if not db_channel:
            await ctx.send('Channel {} is not whitelisted.'.format(channel.mention))
            return

        ctx.session.delete(db_channel)

        logger.info('Removed channel {} on guild {} from whitelist.'
                    .format(*format_named_entities(channel, ctx.guild)))
        await ctx.send('Removed channel {} from whitelist.'.format(channel.mention))

    @whitelist.command('list')
    async def _list(self, ctx: commands.Context):
        """
        Enumerate whitelisted channels on the current server.
        """

        answer = 'Whitelisted channels on this server:```\n'

        channel_list = []

        for db_channel in ctx.session.query(WhitelistedChannel).filter_by(guild_id=ctx.guild.id):
            channel = discord.utils.get(ctx.guild.text_channels, id=db_channel.channel_id)
            if not channel:
                ctx.session.delete(db_channel)
                continue

            channel_list.append(channel)

        channel_list.sort(key=lambda c: c.position)

        for channel in channel_list:
            answer += '#'
            answer += channel.name
            answer += '\n'

        answer += '```'
        await ctx.send(answer)
