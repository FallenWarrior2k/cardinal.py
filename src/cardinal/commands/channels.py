import logging
import discord
import discord.utils
import discord.ext.commands as commands

from cardinal.commands import Cog
from cardinal.db import Session
from cardinal.db.channels import Channel
from cardinal.utils import clean_prefix, channel_whitelisted

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class Channels(Cog):

    def __init__(self, bot):
        super().__init__(bot)

    @commands.group(pass_context=True, no_pm=True, name='channel')
    @channel_whitelisted()
    async def channels(self, ctx):
        """Provides facilities to work with opt-in channels"""
        if ctx.invoked_subcommand is None:
            await self.bot.say('Invalid command passed. Possible choices are "show", "hide", and "opt-in"(mod only). \
                                  \nPlease refer to `{prefix}help {command}` for further information'
                               .format(prefix=clean_prefix(ctx), command=ctx.command.qualified_name))
            return

    @channels.command(pass_context=True, aliases=['show'])
    async def join(self, ctx, *, channel: discord.Channel):
        """Enables a user to access a channel."""
        dbsession = Session()

        channel_db = dbsession.query(Channel).get(channel.id)

        if channel_db:
            role = discord.utils.get(ctx.message.server.roles, id=channel_db.roleid)

            try:
                await self.bot.add_roles(ctx.message.author, role)
            except:
                await self.bot.say('Could not add role, please consult a moderator or try again.')
                return

            await self.bot.say('User {user} joined channel {channel}.'
                               .format(user=ctx.message.author.mention, channel=channel.mention))
        else:
            await self.bot.say('Channel {0} is not specified as an opt-in channel.'.format(channel.mention))

    @channels.command(pass_context=True, aliases=['hide'])
    async def leave(self, ctx, *, channel: discord.Channel = None):
        """Hides a channel from the user's view."""
        if channel is None:
            channel = ctx.message.channel

        dbsession = Session()

        channel_db = dbsession.query(Channel).get(channel.id)

        if channel_db:
            role = discord.utils.get(ctx.message.server.roles, id=channel_db.roleid)

            try:
                await self.bot.remove_roles(ctx.message.author, role)
            except:
                await self.bot.say('Could not remove role, please consult a moderator or try again.')
                return

            await self.bot.say('User {user} left channel {channel}.'
                          .format(user=ctx.message.author.mention, channel=channel.mention))
        else:
            await self.bot.say('Channel {0} is not specified as an opt-in channel.'.format(channel.mention))

    @channels.command(pass_context=True, name='list')
    async def _list(self, ctx):
        """Lists all channels that can be joined through the self.bot."""
        dbsession = Session()
        channel_iter = (channel.name for channel in ctx.message.server.channels if dbsession.query(Channel).get(channel.id))

        answer = 'Channels that can be joined through this bot:```\n'

        for channel in channel_iter:
            answer += '#'
            answer += channel
            answer += '\n'

        answer += '```'

        await self.bot.say(answer)

    @channels.command(pass_context=True)
    async def stats(self, ctx):
        """Shows the member count for each channel."""
        dbsession = Session()
        role_iter = (role for role in ctx.message.server.roles
                     if dbsession.query(Channel).filter_by(roleid=role.id).first())
        role_dict = {}

        for role in role_iter:
            role_dict[role.name] = sum(1 for member in ctx.message.server.members if role in member.roles)

        em = discord.Embed(title='Channel stats for ' + ctx.message.server.name, color=0x38CBF0)
        for role, count in role_dict.items():
            em.add_field(name='#'+role, value=count)

        await self.bot.say(embed=em)

    @channels.group(pass_context=True, name='opt-in')
    @commands.has_permissions(manage_channels=True)
    async def _opt_in(self, ctx):
        """Allows moderators to toggle a channel's opt-in status."""
        if ctx.invoked_subcommand is None:
            await self.bot.say('Invalid command passed: possible options are "enable" and "disable".')

    @_opt_in.command(pass_context=True)
    async def enable(self, ctx, *, channel: discord.Channel = None):
        """Makes a channel opt-in."""
        if channel is None:
            channel = ctx.message.channel

        dbsession = Session()

        if dbsession.query(Channel).get(channel.id):
            await self.bot.say('Channel {0} is already opt-in.'.format(channel.mention))
            return

        try:
            role = await self.bot.create_role(ctx.message.server, name=channel.name)
        except:
            await self.bot.say('Could not make channel {0} opt-in, please consult the dev or try again.'
                               .format(channel.mention))
            await self.bot.say('Error while creating role.')
            return

        everyone_role = ctx.message.server.default_role
        overwrite = discord.PermissionOverwrite()
        overwrite.read_messages = False

        try:
            await self.bot.edit_channel_permissions(channel, everyone_role, overwrite)
        except:
            await self.bot.say('Could not make channel {0} opt-in, please consult the dev or try again'
                               .format(channel.mention))
            await self.bot.say('Error while overriding everyone permissions.')
            return

        overwrite.read_messages = True
        try:
            await self.bot.edit_channel_permissions(channel, role, overwrite)
        except:
            await self.bot.say('Could not make channel {0} opt-in, please consult the dev or try again'
                               .format(channel.mention))
            await self.bot.say('Error while overriding permissions for role members.')

            try:
                await self.bot.edit_channel_permissions(channel, everyone_role, overwrite)
            except:
                await self.bot.say('Could not un-hide the channel. Please do so manually.')

            return

        channel_db = Channel(channelid=channel.id, roleid=role.id)
        dbsession.add(channel_db)
        dbsession.commit()
        await self.bot.say('Opt-in enabled for channel {0}.' .format(channel.mention))

    @_opt_in.command(pass_context=True)
    async def disable(self, ctx, *, channel: discord.Channel = None):
        """Removes a channel's opt-in attribute"""
        if channel is None:
            channel = ctx.message.channel

        dbsession = Session()

        channel_db = dbsession.query(Channel).get(channel.id)

        if channel_db:
            role = discord.utils.get(ctx.message.server.roles, id=channel_db.roleid)

            if role is None:
                await self.bot.say('Could not find role. Was it already deleted?')
            else:
                try:
                    await self.bot.delete_role(ctx.message.server, role)
                except:
                    await self.bot.say('Unable to delete role "{0}". Please do so manually.'.format(role.name))

            everyone_role = ctx.message.server.default_role
            overwrite = discord.PermissionOverwrite()
            overwrite.read_messages = True

            try:
                await self.bot.edit_channel_permissions(channel, everyone_role, overwrite)
            except:
                await self.bot.say('Could not remove opt-in attribute from channel {0}, \
                please consult the dev or try again.'.format(channel.mention))

                await self.bot.say('Unable to un-hide channel {0}. Please do so manually.'.format(channel.mention))

            dbsession.delete(channel_db)
            dbsession.commit()
            await self.bot.say('Opt-in disabled for channel {0}.'.format(channel.mention))
        else:
            await self.bot.say('Channel {0} is not opt-in'.format(channel.mention))