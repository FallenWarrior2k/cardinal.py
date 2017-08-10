import datetime
import logging
import re
import traceback

import discord
import discord.ext.commands as commands

from cardinal.commands import Cog
from cardinal.db import session_scope
from cardinal.db.newbie import User, Guild
from cardinal.utils import clean_prefix, format_discord_user, format_discord_guild

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class Newbies(Cog):
    channel_re = re.compile(
        r'((<#)|^)(?P<id>\d+)(?(2)>|(\s|$))')  # Matches either a channel mention of the form "<#id>" or a raw ID. The actual ID can be extracted from the 'id' group of the match object

    def __init__(self, bot):
        super().__init__(bot)

    async def on_member_join(self, member: discord.Member):
        with session_scope() as session:
            guild = session.query(Guild).get(member.server.id)

            if guild is None:
                return

            paginator = commands.formatter.Paginator(prefix='', suffix='')
            for line in guild.welcome_message.splitlines():
                paginator.add_line(line)

            paginator.add_line()
            paginator.add_line(
                'Please reply with the following message to be granted access to "{}".'.format(member.server.name))
            paginator.add_line('```{}```'.format(guild.response_message))

            user = User(guildid=member.server.id, userid=member.id, joined_at=member.joined_at)
            session.add(user)

            for page in paginator.pages:
                await self.bot.send_message(member, page)

            await self.bot.send_message(member, 'Please note that by staying on "{}", you agree that this bot stores your user ID for identification purposes.\nIt shall be deleted once you confirm the above message or leave the server.'.format(member.server.name))  # Necessary in compliance with Discord's latest ToS changes ¯\_(ツ)_/¯

    async def on_member_leave(self, member: discord.Member):
        with session_scope() as session:
            session.query(User).filter(User.userid == member.id, User.guildid == member.server.id).delete(synchronize_session=False)  # Necessary in compliance with Discord's latest ToS changes ¯\_(ツ)_/¯

    async def on_message(self, msg: discord.Message):
        if msg.author.id == self.bot.user.id:
            return

        if not msg.channel.is_private:
            return

        with session_scope() as session:
            for db_user in session.query(User).filter(User.userid == msg.author.id):
                db_guild = db_user.guild  # Get guild
                if not db_guild:  # If guild not set, delete row
                    session.delete(db_user)
                    continue

                guild = self.bot.get_server(db_user.guildid)
                if not guild:
                    session.delete(db_user)
                    session.delete(db_guild)
                    continue

                member = guild.get_member(msg.author.id)
                if not member:
                    session.delete(db_user)
                    continue

                if db_guild.timeout:
                    joined_interval = datetime.datetime.utcnow() - db_user.joined_at
                    if joined_interval >= db_guild.timeout:
                        try:
                            await self.bot.kick(member)
                        except discord.Forbidden:
                            logger.log(logging.ERROR,
                                       'Lacking permissions to kick user {} from guild {}.'
                                       .format(format_discord_user(member), format_discord_guild(guild)))
                        except discord.HTTPException:
                            logger.log(logging.ERROR,
                                       'Failed kicking user {} from guild {} due to an internal HTTP error.'
                                       .format(format_discord_user(member), format_discord_guild(guild)))
                            logger.log(logging.ERROR, traceback.format_exc())
                        finally:
                            session.delete(db_user)

                        continue

                if not msg.content.lower().strip() == db_guild.response_message.lower():
                    continue

                member_role = discord.utils.get(guild.roles, id=db_guild.roleid)
                if not member_role:
                    continue

                try:
                    await self.bot.add_roles(member, member_role)
                    await self.bot.send_message(msg.author, 'Welcome to {}'.format(guild.name))
                except discord.Forbidden:
                    logger.log(logging.ERROR, 'Lacking permissions to manage roles for user {} on guild {}.'
                               .format(format_discord_user(member), format_discord_guild(guild)))
                except discord.HTTPException as e:
                    logger.log(logging.ERROR, 'Failed managing roles for user {} on guild {} due to HTTP error {}.'
                               .format(format_discord_user(member), format_discord_guild(guild), e.response.status))
                    logger.log(logging.ERROR, traceback.format_exc())
                else:
                    session.delete(db_user)

    @commands.group(pass_context=True, no_pm=True)
    @commands.has_permissions(manage_server=True)
    @commands.bot_has_permissions(manage_roles=True, manage_channels=True)
    async def newbie(self, ctx: commands.Context):
        """Provides functionality for managing automatic newbie roling."""
        if ctx.invoked_subcommand is None:
            await self.bot.say('Invalid subcommand passed, please refer to {}help {} for further information.'.format(
                clean_prefix(ctx), ctx.command.qualified_name))

    @newbie.command(pass_context=True)
    async def enable(self, ctx: commands.Context):
        """Enables automatic newbie roling for the current server.
        This adds a role to new members which restricts their write-privileges, and allows them to only access certain channels."""
        with session_scope() as session:
            if session.query(Guild).get(ctx.message.server.id):
                await self.bot.say('Automated newbie roling is already enabled for this server.')
                return

            everyone_role = ctx.message.server.default_role
            everyone_permissions = everyone_role.permissions
            everyone_permissions.read_messages = False
            everyone_permissions.send_messages = False
            everyone_permissions.read_message_history = False
            member_permissions = discord.Permissions(0x400 | 0x800 | 0x10000)
            overwrite = discord.PermissionOverwrite(read_messages=True)

            await self.bot.say(
                'Please enter the channels that are to remain visible to newbies, separated by spaces.\n_Takes channel mentions, names, and IDs._')
            channels_message = await self.bot.wait_for_message(timeout=60.0, author=ctx.message.author,
                                                               channel=ctx.message.channel)
            if not channels_message:
                await self.bot.say('Terminating process due to timeout.')
                return

            await self.bot.say('Enter the welcome message that should be displayed to new users.')
            welcome_message = await self.bot.wait_for_message(timeout=60.0, author=ctx.message.author,
                                                              channel=ctx.message.channel)
            if not welcome_message:
                await self.bot.say('Terminating process due to timeout.')
                return

            await self.bot.say('Enter the message the user has to respond with.')
            response_message = await self.bot.wait_for_message(timeout=60.0, author=ctx.message.author,
                                                               channel=ctx.message.channel)
            if not response_message:
                await self.bot.say('Terminating process due to timeout.')
                return

            await self.bot.say('Enter a timeout for new users in hours.')
            timeout_message = await self.bot.wait_for_message(timeout=60.0, author=ctx.message.author,
                                                              channel=ctx.message.channel)
            if not timeout_message:
                await self.bot.say('Terminating process due to timeout.')
                return
            try:
                timeout_int = int(timeout_message.content.strip())
            except ValueError:
                timeout_int = 0
                await self.bot.say('The entered value is invalid')

            member_role = await self.bot.create_role(ctx.message.server, name='Member', permissions=member_permissions)
            for member in ctx.message.server.members:
                await self.bot.add_roles(member, member_role)

            await self.bot.edit_role(ctx.message.server, everyone_role, permissions=everyone_permissions)

            for channel in channels_message.content.split():
                match = self.channel_re.match(channel)
                if match:
                    channel_id = match.group('id')
                    channel_obj = discord.utils.get(ctx.message.server.channels, id=channel_id)
                    if channel_obj:
                        await self.bot.edit_channel_permissions(channel_obj, everyone_role, overwrite)

                else:
                    channel_obj = discord.utils.get(ctx.message.server.channels, name=channel.lower())
                    if channel_obj:
                        await self.bot.edit_channel_permissions(channel_obj, member_role, overwrite)

            db_guild = Guild(guildid=ctx.message.server.id, roleid=member_role.id,
                             welcome_message=welcome_message.content.strip(),
                             response_message=response_message.content.strip())

            if timeout_int > 0:
                db_guild.timeout = datetime.timedelta(hours=timeout_int)

            session.add(db_guild)

        await self.bot.say('Automatic newbie roling is now enabled for this server.')

    @newbie.command(pass_context=True)
    async def disable(self, ctx: commands.Context):
        """Disables automatic newbie roling for this server."""
        with session_scope() as session:
            db_guild = session.query(Guild).get(ctx.message.server.id)
            if not db_guild:
                await self.bot.say('Automatic newbie roling is not enabled for this server.')

            role = discord.utils.get(ctx.message.server.roles, id=db_guild.roleid)
            if not role:
                await self.bot.say('Role has already been deleted.')

            everyone_role = ctx.message.server.default_role
            everyone_permissions = everyone_role.permissions
            everyone_permissions.read_messages = True
            everyone_permissions.send_messages = True
            everyone_permissions.read_message_history = True

            await self.bot.edit_role(ctx.message.server, everyone_role, permissions=everyone_permissions)

            await self.bot.delete_role(ctx.message.server, role)
            session.delete(db_guild)

        await self.bot.say('Disabled newbie roling for this server.')
