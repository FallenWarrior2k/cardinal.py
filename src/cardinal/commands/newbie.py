import datetime
import functools
import logging
import re

import discord
import discord.ext.commands as commands

from cardinal.commands import Cog
from cardinal.db import session_scope
from cardinal.db.newbie import User, Guild, Channel
from cardinal.utils import clean_prefix, format_discord_user, format_discord_guild

logger = logging.getLogger(__name__)


def newbie_enabled(func):
    """Decorator to check if newbie roling is enabled before running the command."""

    if isinstance(func, commands.Command):
        cmd = func.callback
    else:
        cmd = func

    @functools.wraps(cmd)
    async def wrapper(*args, **kwargs):
        ctx = next(i for i in args if isinstance(i, commands.Context))  # No try-catch necessary, context is always passed since rewrite
        if ctx:
            with session_scope() as session:
                if not (ctx.guild and session.query(Guild).get(ctx.guild.id)):
                    await ctx.send('Newbie roling is not enabled on this server. Please enable it before using these commands.')
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

    def __init__(self, bot):
        super().__init__(bot)
        # TODO: Scan guilds for non-members who are not in the DB i.e. who joined during a bot downtime
        # TODO: Make background thread that checks for timeouts and kicks the respective users

    async def on_member_join(self, member: discord.Member):
        with session_scope() as session:
            guild = session.query(Guild).get(member.guild.id)

            if guild is None:
                return

            message_content = guild.welcome_message

            message_content += '\n'
            message_content += 'Please reply with the following message to be granted access to "{}".\n'.format(member.guild.name)
            message_content += '```{}```'.format(guild.response_message)

            message = await member.send(message_content)

            user = User(guild_id=member.guild.id, user_id=member.id, message_id=message.id, joined_at=member.joined_at)
            session.add(user)

            await member.send('Please note that by staying on "{}", you agree that this bot stores your user ID for identification purposes.\nIt shall be deleted once you confirm the above message or leave the server.'.format(member.guild.name))  # Necessary in compliance with Discord's latest ToS changes ¯\_(ツ)_/¯

    async def on_member_remove(self, member: discord.Member):
        with session_scope() as session:
            # Using query instead of object deletion to prevent redundant SELECT query
            session.query(User).filter(User.user_id == member.id, User.guild_id == member.guild.id).delete(synchronize_session=False)  # Necessary in compliance with Discord's latest ToS changes ¯\_(ツ)_/¯

    async def on_message(self, msg: discord.Message):
        if msg.author.id == self.bot.user.id:
            return

        if not isinstance(msg.channel, discord.abc.PrivateChannel):
            return

        with session_scope() as session:
            for db_user in session.query(User).filter(User.user_id == msg.author.id):
                db_guild = db_user.guild  # Get guild
                if not db_guild:  # If guild not set, delete row
                    session.delete(db_user)
                    continue

                guild = self.bot.get_guild(db_user.guild_id)
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
                            await member.kick()
                        except discord.Forbidden:
                            logger.exception('Lacking permissions to kick user {} from guild {}.'
                                       .format(format_discord_user(member), format_discord_guild(guild)))
                        except discord.HTTPException as e:
                            logger.exception('Failed kicking user {} from guild {} due to HTTP error {}.'
                                       .format(format_discord_user(member), format_discord_guild(guild), e.response.status))
                        finally:
                            session.delete(db_user)

                        continue

                if not msg.content.lower().strip() == db_guild.response_message.lower():
                    continue

                member_role = discord.utils.get(guild.roles, id=db_guild.role_id)
                if not member_role:
                    continue

                try:
                    await member.add_roles(member_role)
                    await msg.author.send('Welcome to {}'.format(guild.name))
                except discord.Forbidden:
                    logger.exception('Lacking permissions to manage roles for user {} on guild {}.')
                except discord.HTTPException as e:
                    logger.exception('Failed managing roles for user {} on guild {} due to HTTP error {}.'
                               .format(format_discord_user(member), format_discord_guild(guild), e.response.status))

                session.delete(db_user)

    @commands.group()
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(manage_roles=True, manage_channels=True)
    async def newbie(self, ctx: commands.Context):
        """
        Make new members have restricted permissions until they confirm themselves.

        Required context: Server

        Required permissions:
            - Manage Server

        Required bot permissions:
            - Manage Roles
            - Manage Channels
        """

        if ctx.invoked_subcommand is None:
            await ctx.send('Invalid subcommand passed, please refer to `{}help {}` for further information.'
                               .format(clean_prefix(ctx), ctx.command.qualified_name))

    @newbie.command()
    async def enable(self, ctx: commands.Context):
        """
        Enable automatic newbie roling for the current server.
        This will add a role to new members, restricting their permissions to send messages, and additionally restricts their read access to certain channels.
        """
        with session_scope() as session:
            if session.query(Guild).get(ctx.guild.id):
                await ctx.send('Automated newbie roling is already enabled for this server.')
                return

            everyone_role = ctx.guild.default_role
            everyone_permissions = everyone_role.permissions
            everyone_permissions.read_messages = False
            everyone_permissions.send_messages = False
            everyone_permissions.read_message_history = False
            member_permissions = discord.Permissions(0x400 | 0x800 | 0x10000)

            def pred(msg):
                return msg.author.id == ctx.author.id and msg.channel.id == ctx.channel.id

            await ctx.send('Please enter the channels that are to remain visible to newbies, separated by spaces.\n_Takes channel mentions, names, and IDs._')
            channels_message = await self.bot.wait_for('message', check=pred, timeout=60.0)
            if not channels_message:
                await ctx.send('Terminating process due to timeout.')
                return

            await ctx.send('Enter the welcome message that should be displayed to new users.')
            welcome_message = await self.bot.wait_for('message', check=pred, timeout=60.0)
            if not welcome_message:
                await ctx.send('Terminating process due to timeout.')
                return

            await ctx.send('Enter the message the user has to respond with.')
            response_message = await self.bot.wait_for('message', check=pred, timeout=60.0)
            if not response_message:
                await ctx.send('Terminating process due to timeout.')
                return

            await ctx.send('Enter a timeout for new users in hours. Enter 0 to disable timeouts.')
            timeout_message = await self.bot.wait_for('message', check=pred, timeout=60.0)
            if not timeout_message:
                await ctx.send('Terminating process due to timeout.')
                return

            try:
                timeout_int = int(timeout_message.content.strip())
            except ValueError:
                timeout_int = 0
                await ctx.send('The entered value is invalid')

            member_role = await ctx.guild.create_role(name='Member', permissions=member_permissions)
            for member in ctx.guild.members:
                await member.add_roles(member_role)

            await everyone_role.edit(permissions=everyone_permissions)

            db_guild = Guild(guild_id=ctx.guild.id, role_id=member_role.id,
                             welcome_message=welcome_message.content.strip(),
                             response_message=response_message.content.strip())

            if timeout_int > 0:
                db_guild.timeout = datetime.timedelta(hours=timeout_int)

            session.add(db_guild)

            for channel_string in channels_message.content.split():
                match = self.channel_re.match(channel_string)
                if match:
                    channel_id = int(match.group('id'))
                    channel = discord.utils.get(ctx.guild.text_channels, id=channel_id)
                else:
                    channel = discord.utils.get(ctx.guild.text_channels, name=channel_string.lower())

                if channel and channel.guild.id == ctx.guild.id:
                    everyone_overwrite = channel.overwrites_for(everyone_role)
                    everyone_overwrite.update(read_messages=True, read_message_history=True)
                    await channel.set_permissions(everyone_role, overwrite=everyone_overwrite)
                    db_channel = Channel(channel_id=channel.id, guild_id=ctx.guild.id)
                    session.add(db_channel)

        await ctx.send('Automatic newbie roling is now enabled for this server.')

    @newbie.command()
    async def disable(self, ctx: commands.Context):
        """
        Disable automatic newbie roling for this server. New members will instantly have write access, unless verification prevents that.
        """

        with session_scope() as session:
            db_guild = session.query(Guild).get(ctx.guild.id)
            if not db_guild:
                await ctx.send('Automatic newbie roling is not enabled for this server.')

            role = discord.utils.get(ctx.guild.roles, id=db_guild.role_id)
            if not role:
                await ctx.send('Role has already been deleted.')

            everyone_role = ctx.guild.default_role
            member_permissions = role.permissions

            await everyone_role.edit(permissions=member_permissions)
            await role.delete()

            for db_channel in session.query(Channel).filter_by(guild_id=ctx.guild.id):
                channel = discord.utils.get(ctx.guild.text_channels, id=db_channel.channel_id)
                if channel:
                    everyone_overwrite = channel.overwrites_for(everyone_role)
                    everyone_overwrite.update(read_messages=None, read_message_history=None)
                    await channel.set_permissions(everyone_role, overwrite=everyone_overwrite)

            session.delete(db_guild)

        await ctx.send('Disabled newbie roling for this server.')

    @newbie.command()
    @newbie_enabled
    async def timeout(self, ctx: commands.Context, delay: float = 0.0):
        """
        Set the timeout in hours before new users get kicked.
        Put a non-positive value (zero or less) or nothing to remove it.

        Parameters:
            - [optional] delay: A decimal number describing the delay before a kick in hours. Defaults to zero, which means no timeout at all.
        """

        with session_scope() as session:
            db_guild = session.query(Guild).get(ctx.guild.id)

            if delay > 0:
                db_guild.timeout = datetime.timedelta(hours=delay)
            else:
                db_guild.timeout = None

        await ctx.send('Successfully set timeout to {} hours.'.format(delay))

    @newbie.command('welcome-message')
    @newbie_enabled
    async def _welcome_message(self, ctx: commands.Context):
        """
        Set the welcome message for the server.
        """

        await ctx.send('Please enter the message you would like to display to new users.')
        welcome_message = await self.bot.wait_for('message', check=lambda msg: msg.author.id == ctx.author.id and msg.channel.id == ctx.channel.id, timeout=60.0)
        if not welcome_message:
            await ctx.send('Terminating process due to timeout.')
            return

        with session_scope() as session:
            db_guild = session.query(Guild).get(ctx.guild.id)
            db_guild.welcome_message = welcome_message.content

        await ctx.send('Successfully set welcome message.')

    @newbie.command('response-message')
    @newbie_enabled
    async def _response_message(self, ctx: commands.Context, *, msg: str = None):
        """
        Set the response message for the server, i.e. the message users have to enter to be granted access to the server.

        Parameters:
            - [optional] msg: The response message users will have to enter. Defaults to empty, in which case this command will explicitly prompt the caller to enter a message.
        """

        if not msg:
            await ctx.send('Please enter the response message users have to enter upon joining the server.')
            response_message = await self.bot.wait_for('message', check=lambda m: m.author.id == ctx.author.id and m.channel.id == ctx.channel.id, timeout=60.0)
            if not response_message:
                await ctx.send('Terminating process due to timeout.')
                return

            msg = response_message.content

        with session_scope() as session:
            db_guild = session.query(Guild).get(ctx.guild.id)
            db_guild.response_message = msg

            # TODO: Edit already sent messages

        await ctx.send('Successfully set response message.')

    @newbie.group()
    async def channels(self, ctx: commands.Context):
        """
        Modify the channels unconfirmed users can access.
        """

        if ctx.invoked_subcommand is None:
            await ctx.send('Invalid subcommand passed, please refer to `{}help {}` for further information.\nValid options include `add`, `remove` and `list`.'
                               .format(clean_prefix(ctx), ctx.command.qualified_name))
            return

    @channels.command()
    @newbie_enabled
    async def add(self, ctx: commands.Context, *, channel: discord.TextChannel):
        """
        Add a channel to the list of channels unconfirmed users can access.

        Parameters:
            - channel: The channel to add to the list, identified by mention, ID, or name.
        """

        if not channel.guild.id == ctx.guild.id:
            await ctx.send('The provided channel is not on this server.')
            return

        with session_scope() as session:
            if session.query(Channel).get(channel.id):
                await ctx.send('This channel is already visible to unconfirmed users.')
                return

            everyone_role = ctx.guild.default_role
            everyone_overwrite = channel.overwrites_for(everyone_role)
            everyone_overwrite.update(read_messages=True, read_message_history=True)
            await channel.set_permissions(everyone_role, overwrite=everyone_overwrite)

            db_channel = Channel(channel_id=channel.id, guild_id=ctx.guild.id)
            session.add(db_channel)

        await ctx.send('{} is now visible to unconfirmed users.'.format(channel.mention))

    @channels.command()
    @newbie_enabled
    async def remove(self, ctx: commands.Context, *, channel: discord.TextChannel):
        """
        Remove a channel from the list of channels unconfirmed users can access.

        Parameters:
            - channel: The channel to remove from the list, identified by mention, ID, or name.
        """

        if not channel.guild.id == ctx.guild.id:
            await ctx.send('The provided channel is not on this server.')
            return

        with session_scope() as session:
            db_channel = session.query(Channel).get(channel.id)
            if not db_channel:
                await ctx.send('The provided channel is not visible to unconfirmed members.')
                return

            everyone_role = ctx.guild.default_role
            everyone_overwrite = channel.overwrites_for(everyone_role)
            everyone_overwrite.update(read_messages=None, read_message_history=None)
            await channel.set_permissions(everyone_role, overwrite=everyone_overwrite)

            session.delete(db_channel)

        await ctx.send('{} is now invisible to unconfirmed users.'.format(channel.mention))

    @channels.command(pass_context=True)
    @newbie_enabled
    async def list(self, ctx: commands.Context):
        """
        Lists the channels visible to unconfirmed users of this server.
        """

        with session_scope() as session:
            answer = 'The following channels are visible to unconfirmed users of this server.```'
            for db_channel in session.query(Channel).filter(Channel.guild_id == ctx.guild.id):
                channel = discord.utils.get(ctx.guild.text_channels, id=db_channel.channel_id)
                if channel:
                    answer += '#'
                    answer += channel.name
                    answer += '\n'

            answer += '```'

        await ctx.send(answer)
