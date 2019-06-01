from logging import getLogger

from discord import TextChannel
from discord.ext.commands import group, guild_only, has_permissions

from ..context import Context
from ..db import WhitelistedChannel
from ..utils import clean_prefix
from .basecog import BaseCog

logger = getLogger(__name__)


class Whitelisting(BaseCog):
    @group(aliases=['wl'])
    @guild_only()
    async def whitelist(self, ctx: Context):
        """
        Whitelist channels to allow for command usage.

        Required context: Server
        """

        if ctx.invoked_subcommand is None:
            await ctx.send(
                'Invalid command passed. Possible choices are "add" and "remove".\n'
                f'Please refer to `{clean_prefix(ctx)}help {ctx.invoked_with}` '
                'for further information.'
            )
            return

    @whitelist.command()
    @has_permissions(manage_channels=True)
    async def add(self, ctx: Context, *, channel: TextChannel = None):
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
            await ctx.send(f'Channel {channel.mention} is already whitelisted.')
            return

        db_channel = WhitelistedChannel(channel_id=channel.id, guild_id=channel.guild.id)
        ctx.session.add(db_channel)

        logger.info(f'Added channel {channel} on guild {ctx.guild} to whitelist.')
        await ctx.send(f'Whitelisted channel {channel.mention}.')

    @whitelist.command()
    @has_permissions(manage_channels=True)
    async def remove(self, ctx: Context, *, channel: TextChannel = None):
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
            await ctx.send(f'Channel {channel.mention} is not whitelisted.')
            return

        ctx.session.delete(db_channel)

        logger.info(f'Removed channel {channel} on guild {ctx.guild} from whitelist.')
        await ctx.send(f'Removed channel {channel.mention} from whitelist.')

    @whitelist.command('list')
    async def _list(self, ctx: Context):
        """
        Enumerate whitelisted channels on the current server.
        """

        answer = 'Whitelisted channels on this server:```\n'

        channel_list = []

        for db_channel in ctx.session.query(WhitelistedChannel).filter_by(guild_id=ctx.guild.id):
            channel = ctx.guild.get_channel(db_channel.channel_id)
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
