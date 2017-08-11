import discord
import discord.ext.commands as commands

from cardinal.commands import Cog
from cardinal.db import session_scope
from cardinal.db.whitelist import WhitelistedChannel
from cardinal.utils import clean_prefix


class Whitelisting(Cog):
    def __init__(self, bot):
        super().__init__(bot)

    @commands.group(pass_context=True, no_pm=True)
    @commands.has_permissions(manage_channels=True)
    async def whitelist(self, ctx: commands.Context):
        """Provides functionality for whitelisting channels to allow usage of channel-restricted commands."""

        if ctx.invoked_subcommand is None:
            await self.bot.say(
                'Invalid command passed. Possible choices are "add" and "remove".\n Please refer to `{}help {}` for further information.'
                .format(clean_prefix(ctx), ctx.invoked_with))
            return

    @whitelist.command(pass_context=True)
    async def add(self, ctx: commands.Context, *, channel: discord.Channel = None):
        """Adds a channel to the whitelist."""

        if channel is None:
            channel = ctx.message.channel

        with session_scope() as session:
            if session.query(WhitelistedChannel).get(channel.id):
                await self.bot.say('Channel {} is already whitelisted.'.format(channel.mention))
                return

            channel_db = WhitelistedChannel(channelid=channel.id)
            session.add(channel_db)

        await self.bot.say('Whitelisted channel {}.'.format(channel.mention))

    @whitelist.command(pass_context=True)
    async def remove(self, ctx: commands.Context, *, channel: discord.Channel = None):
        """Removes a channel from the whitelist."""

        if channel is None:
            channel = ctx.message.channel

        with session_scope() as session:
            channel_db = session.query(WhitelistedChannel).get(channel.id)
            if not channel_db:
                await self.bot.say('Channel {} is not whitelisted.'.format(channel.mention))
                return

            session.delete(channel_db)
        await self.bot.say('Removed channel {} from whitelist.'.format(channel.mention))
