import logging

import discord
import discord.ext.commands as commands
import discord.utils

from cardinal.commands import Cog
from cardinal.db import session_scope
from cardinal.db.channels import Channel
from cardinal.utils import clean_prefix
from cardinal.checks import channel_whitelisted

logger = logging.getLogger(__name__)


class Channels(Cog):
    def __init__(self, bot):
        super().__init__(bot)

    @commands.group('channel')
    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
    @channel_whitelisted()
    async def channels(self, ctx: commands.Context):
        """
        Access opt-in channels and/or manage them.

        Required context: Server, whitelisted channel

        Required permissions: None

        Required bot permissions:
            - Manage Roles
        """

        if ctx.invoked_subcommand is None:
            await ctx.send('Invalid command passed. Possible choices are "show", "hide", and "opt-in"(mod only).\nPlease refer to `{}help {}` for further information.'
                               .format(clean_prefix(ctx), ctx.command.qualified_name))
            return

    @channels.command(aliases=['show'])
    async def join(self, ctx: commands.Context, *, channel: discord.TextChannel):
        """
        Grant a user access to an opt-in enabled channel.

        Parameters:
            - channel: The channel to join, identified by mention, ID, or name. Please note that due to Discord's client limitations, the first way does not work on mobile.
        """

        with session_scope() as session:
            channel_db = session.query(Channel).get(channel.id)

            if channel_db:
                role = discord.utils.get(ctx.guild.roles, id=channel_db.role_id)

                await ctx.author.add_roles(role, reason='User joined opt-in channel.')

                await ctx.send('User {user} joined channel {channel}.'
                                   .format(user=ctx.author.mention, channel=channel.mention))
            else:
                await ctx.send('Channel {} is not specified as an opt-in channel.'.format(channel.mention))

    @channels.command(aliases=['hide'])
    async def leave(self, ctx: commands.Context, *, channel: discord.TextChannel = None):
        """
        Revoke a user's access to an opt-in enabled channel.

        Parameters:
            - [optional] channel: The channel to leave, identified by mention, ID or name. Defaults to the current channel.
        """

        if channel is None:
            channel = ctx.channel

        with session_scope() as session:
            db_channel = session.query(Channel).get(channel.id)

            if db_channel:
                role = discord.utils.get(ctx.guild.roles, id=db_channel.role_id)

                if not role:
                    session.delete(db_channel)
                    await ctx.send('The role for this channel no longer exists. Removing from database.')
                    return

                await ctx.author.remove_roles(role, reason='User left opt-in channel.')

                await ctx.send('User {user} left channel {channel}.'
                                   .format(user=ctx.author.mention, channel=channel.mention))
            else:
                await ctx.send('Channel {} is not specified as an opt-in channel.'.format(channel.mention))

    @channels.command('list')
    async def _list(self, ctx: commands.Context):
        """
        List all channels that can be joined through the bot.
        """

        with session_scope() as session:
            channel_iter = (discord.utils.get(ctx.guild.text_channels, id=db_channel.channel_id) for db_channel in session.query(Channel).filter_by(guild_id=ctx.guild.id))
            channel_iter = (channel for channel in channel_iter if channel)
            channel_list = sorted(channel_iter, key=lambda r: r.position)

        answer = 'Channels that can be joined through this bot:```\n'

        for channel in channel_list:
            answer += '#'
            answer += channel.name
            answer += '\n'

        answer += '```'

        await ctx.send(answer)

    @channels.command()
    async def stats(self, ctx: commands.Context):
        """
        Display the member count for each opt-in channel on the current server.
        """

        with session_scope() as session:
            role_iter = (discord.utils.get(ctx.guild.roles, id=db_role.id) for db_role in session.query(Channel).filter_by(guild_id=ctx.guild.id))
            role_dict = dict((role, sum(1 for member in ctx.guild.members if role in member.roles))
                             for role in role_iter if role)

        em = discord.Embed(title='Channel stats for ' + ctx.guild.name, color=0x38CBF0)
        for role in sorted(role_dict.keys(), key=lambda r: r.position):
            em.add_field(name='#' + role.name, value=role_dict[role])

        await ctx.send(embed=em)

    @channels.group('opt-in', )
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def _opt_in(self, ctx: commands.Context):
        """
        Allows moderators to toggle a channel's opt-in status.

        Required permissions:
            - Manage Channels

        Required bot permissions:
            - Manage Channels
        """

        if ctx.invoked_subcommand is None:
            await ctx.send('Invalid command passed: possible options are "enable" and "disable".')

    @_opt_in.command()
    async def enable(self, ctx: commands.Context, *, channel: discord.TextChannel = None):
        """
        Make a channel opt-in, revoking access for @\u200beveryone and granting it only to a specifically created role.

        Parameters:
            - [optional] channel: The channel to mark as opt-in, identified by mention, ID, or name. Defaults to the current channel.
        """

        if channel is None:
            channel = ctx.channel

        with session_scope() as session:
            if session.query(Channel).get(channel.id):
                await ctx.send('Channel {} is already opt-in.'.format(channel.mention))
                return

            role = await ctx.guild.create_role(reason='Opt-in role for channel "{}"'.format(channel.name), name=channel.name)

            everyone_role = ctx.guild.default_role

            await channel.set_permissions(everyone_role, read_messages=False)
            await channel.set_permissions(role, read_message=True)

            db_channel = Channel(channel_id=channel.id, role_id=role.id, guild_id=channel.guild.id)
            session.add(db_channel)

        await ctx.send('Opt-in enabled for channel {}.'.format(channel.mention))

    @_opt_in.command()
    async def disable(self, ctx: commands.Context, *, channel: discord.TextChannel = None):
        """
        Remove the opt-in status from a channel, making it accessible for @\u200beveryone again.

        Parameters:
            - [optional] channel: The channe to mark as public, identified by mention, ID, or name. Defaults to the current channel.
        """
        if channel is None:
            channel = ctx.channel

        with session_scope as session:
            db_channel = session.query(Channel).get(channel.id)

            if db_channel:
                role = discord.utils.get(ctx.guild.roles, id=db_channel.role_id)

                if role is None:
                    await ctx.send('Could not find role. Was it already deleted?')
                else:
                    await role.delete()

                everyone_role = ctx.guild.default_role

                await channel.set_permissions(everyone_role, read_messages=True)

                session.delete(db_channel)
                await ctx.send('Opt-in disabled for channel {}.'.format(channel.mention))
            else:
                await ctx.send('Channel {} is not opt-in'.format(channel.mention))
