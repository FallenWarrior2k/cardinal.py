import logging

import discord
import discord.ext.commands as commands
import discord.utils

from cardinal.commands import Cog
from cardinal.db import session_scope
from cardinal.db.channels import Channel
from cardinal.utils import clean_prefix, channel_whitelisted

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class Channels(Cog):
    def __init__(self, bot):
        super().__init__(bot)

    @commands.group(pass_context=True, no_pm=True, name='channel')
    @commands.bot_has_permissions(manage_roles=True)
    @channel_whitelisted()
    async def channels(self, ctx: commands.Context):
        """Provides facilities to work with opt-in channels"""

        if ctx.invoked_subcommand is None:
            await self.bot.say('Invalid command passed. Possible choices are "show", "hide", and "opt-in"(mod only). \
                                  \nPlease refer to `{}help {}` for further information'
                               .format(clean_prefix(ctx), ctx.command.qualified_name))
            return

    @channels.command(pass_context=True, aliases=['show'])
    async def join(self, ctx, *, channel: discord.Channel):
        """Enables a user to access a channel."""

        with session_scope() as session:
            channel_db = session.query(Channel).get(channel.id)

            if channel_db:
                role = discord.utils.get(ctx.message.server.roles, id=channel_db.role_id)

                await self.bot.add_roles(ctx.message.author, role)

                await self.bot.say('User {user} joined channel {channel}.'
                                   .format(user=ctx.message.author.mention, channel=channel.mention))
            else:
                await self.bot.say('Channel {} is not specified as an opt-in channel.'.format(channel.mention))

    @channels.command(pass_context=True, aliases=['hide'])
    async def leave(self, ctx, *, channel: discord.Channel = None):
        """Hides a channel from the user's view."""

        if channel is None:
            channel = ctx.message.channel

        with session_scope() as session:
            channel_db = session.query(Channel).get(channel.id)

            if channel_db:
                role = discord.utils.get(ctx.message.server.roles, id=channel_db.role_id)

                await self.bot.remove_roles(ctx.message.author, role)

                await self.bot.say('User {user} left channel {channel}.'
                                   .format(user=ctx.message.author.mention, channel=channel.mention))
            else:
                await self.bot.say('Channel {} is not specified as an opt-in channel.'.format(channel.mention))

    @channels.command(pass_context=True, name='list')
    async def _list(self, ctx: commands.Context):
        """Lists all channels that can be joined through the self.bot."""

        with session_scope() as session:
            channel_iter = (channel for channel in ctx.message.server.channels if
                            session.query(Channel).get(channel.id))
            channel_list = sorted(channel_iter, key=lambda r: r.position)

        answer = 'Channels that can be joined through this bot:```\n'

        for channel in channel_list:
            answer += '#'
            answer += channel.name
            answer += '\n'

        answer += '```'

        await self.bot.say(answer)

    @channels.command(pass_context=True)
    async def stats(self, ctx: commands.Context):
        """Shows the member count for each channel."""

        with session_scope() as session:
            role_dict = dict((role, sum(1 for member in ctx.message.server.members if role in member.roles))
                             for role in ctx.message.server.roles
                             if session.query(Channel).filter_by(role_id=role.id).first())

        em = discord.Embed(title='Channel stats for ' + ctx.message.server.name, color=0x38CBF0)
        for role in sorted(role_dict.keys(), key=lambda r: r.position):
            em.add_field(name='#' + role.name, value=role_dict[role])

        await self.bot.say(embed=em)

    @channels.group(pass_context=True, name='opt-in')
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def _opt_in(self, ctx: commands.Context):
        """Allows moderators to toggle a channel's opt-in status."""

        if ctx.invoked_subcommand is None:
            await self.bot.say('Invalid command passed: possible options are "enable" and "disable".')

    @_opt_in.command(pass_context=True)
    async def enable(self, ctx: commands.Context, *, channel: discord.Channel = None):
        """Makes a channel opt-in."""

        if channel is None:
            channel = ctx.message.channel

        with session_scope() as session:
            if session.query(Channel).get(channel.id):
                await self.bot.say('Channel {} is already opt-in.'.format(channel.mention))
                return

            role = await self.bot.create_role(ctx.message.server, name=channel.name)

            everyone_role = ctx.message.server.default_role
            overwrite = discord.PermissionOverwrite()
            overwrite.read_messages = False

            await self.bot.edit_channel_permissions(channel, everyone_role, overwrite)

            overwrite.read_messages = True
            await self.bot.edit_channel_permissions(channel, role, overwrite)

            channel_db = Channel(channel_id=channel.id, role_id=role.id)
            session.add(channel_db)

        await self.bot.say('Opt-in enabled for channel {}.'.format(channel.mention))

    @_opt_in.command(pass_context=True)
    async def disable(self, ctx: commands.Context, *, channel: discord.Channel = None):
        """Removes a channel's opt-in attribute"""
        if channel is None:
            channel = ctx.message.channel

        with session_scope as session:
            channel_db = session.query(Channel).get(channel.id)

            if channel_db:
                role = discord.utils.get(ctx.message.server.roles, id=channel_db.role_id)

                if role is None:
                    await self.bot.say('Could not find role. Was it already deleted?')
                else:
                    await self.bot.delete_role(ctx.message.server, role)

                everyone_role = ctx.message.server.default_role
                overwrite = discord.PermissionOverwrite()
                overwrite.read_messages = True

                await self.bot.edit_channel_permissions(channel, everyone_role, overwrite)

                session.delete(channel_db)
                await self.bot.say('Opt-in disabled for channel {}.'.format(channel.mention))
            else:
                await self.bot.say('Channel {} is not opt-in'.format(channel.mention))
