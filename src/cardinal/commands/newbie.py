import datetime
import functools
import logging
import re
import traceback

import discord
import discord.ext.commands as commands

from cardinal.commands import Cog
from cardinal.db import session_scope
from cardinal.db.newbie import User, Guild, Channel
from cardinal.utils import clean_prefix, format_discord_user, format_discord_guild

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def newbie_enabled(func):
    """Decorator to check if newbie roling is enabled before running the command."""

    if isinstance(func, commands.Command):
        cmd = func.callback
    else:
        cmd = func

    @functools.wraps(cmd)
    async def wrapper(*args, **kwargs):
        _self = args[0]
        ctx = args[1]
        if ctx:
            with session_scope() as session:
                if not (ctx.message.server and session.query(Guild).get(ctx.message.server.id)):
                    await _self.bot.say('Newbie roling is not enabled on this server. Please enable it before using these commands.')
                    return

        await cmd(*args, **kwargs)

    if isinstance(func, commands.Command):
        func.callback = wrapper
        return func
    else:
        return wrapper


class Newbies(Cog):
    channel_re = re.compile(
        r'((<#)|^)(?P<id>\d+)(?(2)>|(\s|$))')  # Matches either a channel mention of the form "<#id>" or a raw ID. The actual ID can be extracted from the 'id' group of the match object

    everyone_overwrite = discord.PermissionOverwrite(read_messages=True)

    def __init__(self, bot):
        super().__init__(bot)
        # TODO: Scan guilds for non-members who are not in the DB i.e. who joined during a bot downtime

    async def on_member_join(self, member: discord.Member):
        with session_scope() as session:
            guild = session.query(Guild).get(member.server.id)

            if guild is None:
                return

            message_content = guild.welcome_message

            message_content += '\n'
            message_content += 'Please reply with the following message to be granted access to "{}".\n'.format(member.server.name)
            message_content += '```{}```'.format(guild.response_message)

            message = await self.bot.send_message(member, message_content)

            user = User(guild_id=member.server.id, userid=member.id, message_id=message.id, joined_at=member.joined_at)
            session.add(user)

            await self.bot.send_message(member, 'Please note that by staying on "{}", you agree that this bot stores your user ID for identification purposes.\nIt shall be deleted once you confirm the above message or leave the server.'.format(member.server.name))  # Necessary in compliance with Discord's latest ToS changes ¯\_(ツ)_/¯

    async def on_member_remove(self, member: discord.Member):
        with session_scope() as session:
            # Using query instead of object deletion to prevent redundant SELECT query
            session.query(User).filter(User.user_id == member.id, User.guild_id == member.server.id).delete(synchronize_session=False)  # Necessary in compliance with Discord's latest ToS changes ¯\_(ツ)_/¯

    async def on_message(self, msg: discord.Message):
        if msg.author.id == self.bot.user.id:
            return

        if not msg.channel.is_private:
            return

        with session_scope() as session:
            for db_user in session.query(User).filter(User.user_id == msg.author.id):
                db_guild = db_user.guild  # Get guild
                if not db_guild:  # If guild not set, delete row
                    session.delete(db_user)
                    continue

                guild = self.bot.get_server(db_user.guild_id)
                if not guild:
                    # session.delete(db_user)  # Unnecessary because ON DELETE CASCADE / 'delete-orphan' should clean it up automatically
                    session.delete(db_guild)  # Delete guild if bot no longer has access to it
                    continue

                member = guild.get_member(msg.author.id)
                if not member:
                    session.delete(db_user)  # Delete row if user already left
                    continue

                if db_guild.timeout:
                    joined_interval = datetime.datetime.utcnow() - db_user.joined_at  # Use utcnow because discord.py's join timestamps are in UTC
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

                member_role = discord.utils.get(guild.roles, id=db_guild.role_id)
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

                session.delete(db_user)

    @commands.group(pass_context=True, no_pm=True)
    @commands.has_permissions(manage_server=True)
    @commands.bot_has_permissions(manage_roles=True, manage_channels=True)
    async def newbie(self, ctx: commands.Context):
        """Provides functionality for managing automatic newbie roling."""

        if ctx.invoked_subcommand is None:
            await self.bot.say('Invalid subcommand passed, please refer to `{}help {}` for further information.'
                               .format(clean_prefix(ctx), ctx.command.qualified_name))

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

            await self.bot.say('Please enter the channels that are to remain visible to newbies, separated by spaces.\n_Takes channel mentions, names, and IDs._')
            channels_message = await self.bot.wait_for_message(timeout=60.0, author=ctx.message.author, channel=ctx.message.channel)
            if not channels_message:
                await self.bot.say('Terminating process due to timeout.')
                return

            await self.bot.say('Enter the welcome message that should be displayed to new users.')
            welcome_message = await self.bot.wait_for_message(timeout=60.0, author=ctx.message.author, channel=ctx.message.channel)
            if not welcome_message:
                await self.bot.say('Terminating process due to timeout.')
                return

            await self.bot.say('Enter the message the user has to respond with.')
            response_message = await self.bot.wait_for_message(timeout=60.0, author=ctx.message.author, channel=ctx.message.channel)
            if not response_message:
                await self.bot.say('Terminating process due to timeout.')
                return

            await self.bot.say('Enter a timeout for new users in hours. Enter 0 to disable timeouts.')
            timeout_message = await self.bot.wait_for_message(timeout=60.0, author=ctx.message.author, channel=ctx.message.channel)
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

            db_guild = Guild(guild_id=ctx.message.server.id, role_id=member_role.id,
                             welcome_message=welcome_message.content.strip(),
                             response_message=response_message.content.strip())

            if timeout_int > 0:
                db_guild.timeout = datetime.timedelta(hours=timeout_int)

            session.add(db_guild)

            for channel in channels_message.content.split():
                match = self.channel_re.match(channel)
                if match:
                    channel_id = match.group('id')
                    channel_obj = discord.utils.get(ctx.message.server.channels, id=channel_id)
                    if channel_obj and channel_obj.server.id == ctx.message.server.id:
                        await self.bot.edit_channel_permissions(channel_obj, everyone_role, self.everyone_overwrite)
                        db_channel = Channel(channel_id=channel_obj.id, guild_id=ctx.message.server.id)
                        session.add(db_channel)

                else:
                    channel_obj = discord.utils.get(ctx.message.server.channels, name=channel.lower())
                    if channel_obj:
                        await self.bot.edit_channel_permissions(channel_obj, member_role, self.everyone_overwrite)

        await self.bot.say('Automatic newbie roling is now enabled for this server.')

    @newbie.command(pass_context=True)
    async def disable(self, ctx: commands.Context):
        """Disables automatic newbie roling for this server."""

        with session_scope() as session:
            db_guild = session.query(Guild).get(ctx.message.server.id)
            if not db_guild:
                await self.bot.say('Automatic newbie roling is not enabled for this server.')

            role = discord.utils.get(ctx.message.server.roles, id=db_guild.role_id)
            if not role:
                await self.bot.say('Role has already been deleted.')

            everyone_role = ctx.message.server.default_role
            # everyone_permissions = everyone_role.permissions
            # everyone_permissions.read_messages = True
            # everyone_permissions.send_messages = True
            # everyone_permissions.read_message_history = True
            everyone_permissions = role.permissions

            await self.bot.edit_role(ctx.message.server, everyone_role, permissions=everyone_permissions)

            await self.bot.delete_role(ctx.message.server, role)
            session.delete(db_guild)

        await self.bot.say('Disabled newbie roling for this server.')

    @newbie.command(pass_context=True)
    @newbie_enabled
    async def timeout(self, ctx: commands.Context, delay: float = 0.0):
        """
        Sets the timeout in hours before new users get kicked.
        Put a non-positive value (zero or less) or nothing to remove it.
        """

        with session_scope() as session:
            db_guild = session.query(Guild).get(ctx.message.server.id)

            if delay > 0:
                db_guild.timeout = datetime.timedelta(hours=delay)
            else:
                db_guild.timeout = None

        await self.bot.say('Successfully set timeout to {} hours.'.format(delay))

    @newbie.command(pass_context=True, name='welcome-message')
    @newbie_enabled
    async def _welcome_message(self, ctx: commands.Context):
        """Sets the welcome message for the server."""

        await self.bot.say('Please enter the message you would like to display to new users.')
        welcome_message = await self.bot.wait_for_message(timeout=60.0, author=ctx.message.author, channel=ctx.message.channel)
        if not welcome_message:
            await self.bot.say('Terminating process due to timeout.')
            return

        with session_scope() as session:
            db_guild = session.query(Guild).get(ctx.message.server.id)
            db_guild.welcome_message = welcome_message.content

        await self.bot.say('Successfully set welcome message.')

    @newbie.command(pass_context=True, name='response-message')
    @newbie_enabled
    async def _response_message(self, ctx: commands.Context, *, msg: str = None):
        """Sets the response message for the server."""

        if not msg:
            await self.bot.say('Please enter the response message users have to enter upon joining the server.')
            response_message = await self.bot.wait_for_message(timeout=60.0, author=ctx.message.author, channel=ctx.message.channel)
            if not response_message:
                await self.bot.say('Terminating process due to timeout.')
                return

            msg = response_message.content

        with session_scope() as session:
            db_guild = session.query(Guild).get(ctx.message.server.id)
            db_guild.response_message = msg

        await self.bot.say('Successfully set response message.')

    @newbie.group(pass_context=True)
    async def channels(self, ctx: commands.Context):
        """Modifies the channels unconfirmed users can access."""

        if ctx.invoked_subcommand is None:
            await self.bot.say('Invalid subcommand passed, please refer to `{}help {}` for further information.\nValid options include `add`, `remove` and `list`.'
                               .format(clean_prefix(ctx), ctx.command.qualified_name))
            return

    @channels.command(pass_context=True)
    @newbie_enabled
    async def add(self, ctx: commands.Context, *, channel: discord.Channel):
        """Adds a channel to the list of channels unconfirmed users can access."""

        if not channel.server.id == ctx.message.server.id:
            await self.bot.say('The provided channel is not on this server.')
            return

        with session_scope() as session:
            if session.query(Channel).get(channel.id):
                await self.bot.say('This channel is already visible to unconfirmed users.')
                return

            everyone_role = ctx.message.server.default_role
            await self.bot.edit_channel_permissions(channel, everyone_role, self.everyone_overwrite)

            db_channel = Channel(channel_id=channel.id, guild_id=ctx.message.server.id)
            session.add(db_channel)

        await self.bot.say('{} is now visible to unconfirmed users.'.format(channel.mention))

    @channels.command(pass_context=True)
    @newbie_enabled
    async def remove(self, ctx: commands.Context, *, channel: discord.Channel):
        """Removes a channel from the list of channels unconfirmed users can access."""

        if not channel.server.id == ctx.message.server.id:
            await self.bot.say('The provided channel is not on this server.')
            return

        with session_scope() as session:
            db_channel = session.query(Channel).get(channel.id)
            if not db_channel:
                await self.bot.say('The provided channel is not visible to unconfirmed members.')
                return

            everyone_role = ctx.message.server.default_role
            await self.bot.edit_channel_permissions(channel, everyone_role)

            session.delete(db_channel)

        await self.bot.say('{} is now invisble to unconfirmed users.'.format(channel.mention))

    @channels.command(pass_context=True)
    @newbie_enabled
    async def list(self, ctx: commands.Context):
        """Lists the channels visible to unconfirmed users of this server."""

        with session_scope() as session:
            answer = 'The following channels are visible to unconfirmed users of this server.```'
            for db_channel in session.query(Channel).filter(Channel.guild_id == ctx.message.server.id):
                channel = discord.utils.get(ctx.message.server.channels, id=db_channel.channel_id)
                if channel:
                    answer += '#'
                    answer += channel.name
                    answer += '\n'

            answer += '```'

        await self.bot.say(answer)
