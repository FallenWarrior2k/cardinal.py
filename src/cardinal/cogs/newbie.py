import asyncio
import logging
import re
from datetime import datetime, timedelta
from functools import partial, wraps

import discord
from discord.ext import commands

from ..context import Context
from ..db import NewbieChannel, NewbieGuild, NewbieUser
from ..errors import PromptTimeout
from ..utils import clean_prefix, prompt
from .basecog import BaseCog

logger = logging.getLogger(__name__)

# Matches either a channel mention of the form "<#id>" or a raw ID.
# The actual ID can be extracted from the 'id' group of the match object
channel_re = re.compile(r'((<#)|^)(?P<id>\d+)(?(2)>|(\s|$))')


def newbie_enabled(func):
    """Decorator to check if newbie roling is enabled before running the command."""

    if isinstance(func, commands.Command):
        cmd = func.callback
    else:
        cmd = func

    @wraps(cmd)
    async def wrapper(*args, **kwargs):
        # No try-catch necessary, context is always passed since rewrite
        ctx = next(i for i in args if isinstance(i, Context))

        if not (ctx.guild and ctx.session.query(NewbieGuild).get(ctx.guild.id)):
            await ctx.send('Newbie roling is not enabled on this server. '
                           'Please enable it before using these commands.')
            return

        await cmd(*args, **kwargs)

    if isinstance(func, commands.Command):
        func.callback = wrapper
        return func
    else:
        return wrapper


class Newbies(BaseCog):
    def __init__(self, bot):
        super().__init__(bot)
        self.bot.loop.create_task(self.check_timeouts())

    async def check_timeouts(self):
        await self.bot.wait_until_ready()
        while True:
            with self.bot.session_scope() as session:
                # Get users who have passed the timeout
                # !IMPORTANT! Filter inequation must not be changed
                # Changing it will break SQLite support (and possibly other DBMSs as well)
                q = session.query(NewbieUser)\
                    .join(NewbieUser.guild)\
                    .filter(datetime.utcnow() > NewbieGuild.timeout + NewbieUser.joined_at)

                for db_user in q:
                    guild = self.bot.get_guild(db_user.guild_id)
                    if not guild:
                        continue

                    member = guild.get_member(db_user.user_id)
                    if not member:
                        session.delete(db_user)
                        continue

                    try:
                        await member.kick(reason='Verification timed out.')
                        session.delete(db_user)
                        logger.info('Kicked overdue user {} from guild {}.'.format(member, guild))
                    except discord.Forbidden:
                        logger.exception('Lacking permissions to kick user {} from guild {}.'
                                         .format(member, guild))
                    except discord.HTTPException as e:
                        logger.exception(
                            'Failed to kick user {} from guild {} due to HTTP error {}.'
                            .format(member, guild, e.response.status))

            await asyncio.sleep(60)

    @staticmethod
    async def add_member(session, db_guild: NewbieGuild, member: discord.Member):
        if session.query(NewbieUser).get((member.id, db_guild.guild_id)):
            return  # Exit if user already in DB

        message_content = db_guild.welcome_message

        message_content += '\n'
        message_content += 'Please reply with the following message ' \
                           'to be granted access to "{}".\n'.format(member.guild.name)
        message_content += '```{}```'.format(db_guild.response_message)

        try:
            message = await member.send(message_content)
        except discord.Forbidden:
            logger.exception('Cannot message user {} and thus cannot prompt for verification.'
                             .format(member))
            return
        except discord.HTTPException as e:
            logger.exception('Failed sending message to user {} due to HTTP error {}.'
                             .format(member, e.response.status))
            return
        else:
            # Use utcnow() instead of join time to treat members who got the message too late fairly
            db_user = NewbieUser(guild_id=member.guild.id,
                                 user_id=member.id,
                                 message_id=message.id,
                                 joined_at=datetime.utcnow())
            session.add(db_user)
            session.commit()
            logger.info('Added new user {} to database for guild {}.'.format(member, member.guild))

            try:
                # Necessary in compliance with Discord's latest ToS changes ¯\_(ツ)_/¯
                await member.send(
                    'Please note that by staying on "{}", '
                    'you agree that this bot stores your user ID for identification purposes.\n'
                    'It shall be deleted once you confirm the above message or leave the server.'
                    .format(member.guild.name))
            except discord.HTTPException:
                # First message went through, no need to further handle this, should it ever occur
                pass

    @commands.Cog.listener()
    async def on_ready(self):
        with self.bot.session_scope() as session:
            for db_guild in session.query(NewbieGuild):
                guild = self.bot.get_guild(db_guild.guild_id)
                if not guild:
                    continue

                member_role = guild.get_role(db_guild.role_id)
                if not member_role:
                    continue

                to_add = (member for member in guild.members if member_role not in member.roles)
                for member in to_add:
                    await self.add_member(session, db_guild, member)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        with self.bot.session_scope() as session:
            db_guild = session.query(NewbieGuild).get(member.guild.id)

            if db_guild is None:
                return

            # Bots don't need confirmation, since they were manually added by a mod/admin
            # Not like they could confirm themselves anyways
            if member.bot:
                role = member.guild.get_role(db_guild.role_id)
                if not role:
                    return

                await member.add_roles(role)
                return

            await self.add_member(session, db_guild, member)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        with self.bot.session_scope() as session:
            # Necessary in compliance with Discord's latest ToS changes ¯\_(ツ)_/¯
            # Use query instead of object deletion to prevent redundant SELECT query
            session.query(NewbieUser)\
                .filter(NewbieUser.user_id == member.id, NewbieUser.guild_id == member.guild.id)\
                .delete(synchronize_session=False)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        with self.bot.session_scope() as session:
            db_user = session.query(NewbieUser).get((before.id, before.guild.id))

            if not db_user:
                return

            role = before.guild.get_role(db_user.guild.role_id)

            if not role:
                return

            if role not in before.roles and role in after.roles:
                session.delete(db_user)

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        if msg.author.id == self.bot.user.id:
            return

        if not isinstance(msg.channel, discord.abc.PrivateChannel):
            return

        with self.bot.session_scope() as session:
            for db_user in session.query(NewbieUser).filter(NewbieUser.user_id == msg.author.id):
                db_guild = db_user.guild

                guild = self.bot.get_guild(db_user.guild_id)
                if not guild:
                    continue

                member = guild.get_member(msg.author.id)
                if not member:
                    session.delete(db_user)  # Delete row if user already left
                    continue

                if db_guild.timeout:
                    # Use utcnow because discord.py's join timestamps are in UTC
                    joined_interval = datetime.utcnow() - db_user.joined_at
                    if joined_interval >= db_guild.timeout:
                        try:
                            await member.kick()
                        except discord.Forbidden:
                            logger.exception('Lacking permissions to kick user {} from guild {}.'
                                             .format(member, guild))
                        except discord.HTTPException as e:
                            logger.exception(
                                'Failed to kick user {} from guild {} due to HTTP error {}.'
                                .format(member, guild, e.response.status))
                        finally:
                            session.delete(db_user)

                        continue

                if not msg.content.lower().strip() == db_guild.response_message.lower():
                    continue

                member_role = guild.get_role(db_guild.role_id)
                if not member_role:
                    continue

                try:
                    await member.add_roles(member_role)

                    session.delete(db_user)
                    logger.info('Verified user {} on guild {}.'.format(member, guild))

                    await msg.author.send('Welcome to {}'.format(guild.name))
                except discord.Forbidden:
                    logger.exception('Lacking permissions to manage roles for user {} on guild {}.')
                except discord.HTTPException as e:
                    logger.exception(
                        'Failed to manage roles for user {} on guild {} due to HTTP error {}.'
                        .format(member, guild, e.response.status))

    @commands.group()
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(manage_roles=True, manage_channels=True)
    async def newbie(self, ctx: Context):
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
            await ctx.send(
                'Invalid subcommand passed, please refer to `{}help {}` for further information.'
                .format(clean_prefix(ctx), ctx.command.qualified_name))

    @newbie.command()
    async def enable(self, ctx: Context):
        """
        Enable automatic newbie roling for the current server.
        This will add a role to new members, restricting their permissions to send messages,
        and additionally restricts their read access to certain channels.
        """

        if ctx.session.query(NewbieGuild).get(ctx.guild.id):
            await ctx.send('Automated newbie roling is already enabled for this server.')
            return

        everyone_role = ctx.guild.default_role
        everyone_permissions = everyone_role.permissions
        everyone_permissions.read_messages = False
        everyone_permissions.send_messages = False
        everyone_permissions.read_message_history = False
        member_permissions = discord.Permissions(0x400 | 0x800 | 0x10000)

        bound_prompt = partial(prompt, ctx=ctx)

        try:
            channels_message = await bound_prompt(
                'Please enter the channels that are to remain visible to newbies, '
                'separated by spaces.\n_Takes channel mentions, names, and IDs._')

            welcome_message = await bound_prompt(
                'Enter the welcome message that should be displayed to new users.')

            response_message = await bound_prompt('Enter the message the user has to respond with.')

            timeout_message = await bound_prompt(
                'Enter a timeout for new users in hours. Enter 0 to disable timeouts.'
            )
        except PromptTimeout:
            await ctx.send('Terminating process due to timeout.')
            return

        try:
            timeout_int = int(timeout_message.content.strip())
        except ValueError:
            timeout_int = 0
            await ctx.send('The entered value is invalid. Disabling timeouts.')

        member_role = await ctx.guild.create_role(name='Member', permissions=member_permissions)
        for member in ctx.guild.members:
            await member.add_roles(member_role)

        await everyone_role.edit(permissions=everyone_permissions)

        db_guild = NewbieGuild(guild_id=ctx.guild.id, role_id=member_role.id,
                               welcome_message=welcome_message.content.strip(),
                               response_message=response_message.content.strip())

        if timeout_int > 0:
            db_guild.timeout = timedelta(hours=timeout_int)

        ctx.session.add(db_guild)

        for channel_string in channels_message.content.split():
            match = channel_re.match(channel_string)
            if match:
                channel_id = int(match.group('id'))
                channel = ctx.guild.get_channel(channel_id)
            else:
                channel = discord.utils.get(ctx.guild.text_channels, name=channel_string.lower())

            if channel and channel.guild.id == ctx.guild.id:
                everyone_overwrite = channel.overwrites_for(everyone_role)
                everyone_overwrite.update(read_messages=True, read_message_history=True)
                await channel.set_permissions(everyone_role, overwrite=everyone_overwrite)
                db_channel = NewbieChannel(channel_id=channel.id, guild_id=ctx.guild.id)
                ctx.session.add(db_channel)

        logger.info('Enabled newbie roling on guild {}.'.format(ctx.guild))
        await ctx.send('Automatic newbie roling is now enabled for this server.')

    @newbie.command()
    async def disable(self, ctx: Context):
        """
        Disable automatic newbie roling for this server.
        New members will instantly have write access, unless verification prevents that.
        """

        db_guild = ctx.session.query(NewbieGuild).get(ctx.guild.id)
        if not db_guild:
            await ctx.send('Automatic newbie roling is not enabled for this server.')
            return

        role = ctx.guild.get_role(db_guild.role_id)
        if not role:
            await ctx.send('Role has already been deleted.')
            return

        everyone_role = ctx.guild.default_role
        everyone_perms = everyone_role.permissions
        member_perms = role.permissions

        # Copy old everyone perms and additionally grant perms on member role
        merged_perms = discord.Permissions(everyone_perms.value)
        merged_perms.update(**{perm: val for perm, val in member_perms if val})

        await everyone_role.edit(permissions=merged_perms)
        await role.delete()

        for db_channel in ctx.session.query(NewbieChannel).filter_by(guild_id=ctx.guild.id):
            channel = ctx.guild.get_channel(db_channel.channel_id)
            if not channel:
                continue

            everyone_overwrite = channel.overwrites_for(everyone_role)
            everyone_overwrite.update(read_messages=None, read_message_history=None)
            await channel.set_permissions(everyone_role, overwrite=everyone_overwrite)

        ctx.session.delete(db_guild)

        logger.info('Disabled newbie roling on guild {}.'.format(ctx.guild))
        await ctx.send('Disabled newbie roling for this server.')

    @newbie.command()
    @newbie_enabled
    async def timeout(self, ctx: Context, delay: int = 0):
        """
        Set the timeout in hours before new users get kicked.
        Put a non-positive value (zero or less) or nothing to remove it.

        Parameters:
            - [optional] delay: A decimal number describing the delay before a kick in hours.
            Defaults to zero, which means no timeout at all.
        """

        db_guild = ctx.session.query(NewbieGuild).get(ctx.guild.id)

        if delay > 0:
            db_guild.timeout = timedelta(hours=delay)
        else:
            db_guild.timeout = None

        logger.info('Changed timeout for {} to {} hours.'.format(ctx.guild, delay))
        await ctx.send('Successfully set timeout to {} hours.'.format(delay))

    @newbie.command('welcome-message')
    @newbie_enabled
    async def _welcome_message(self, ctx: Context):
        """
        Set the welcome message for the server.
        """

        try:
            welcome_message = await prompt(
                'Please enter the message you would like to display to new users.',
                ctx
            )
        except PromptTimeout:
            await ctx.send('Terminating process due to timeout.')
            return

        db_guild = ctx.session.query(NewbieGuild).get(ctx.guild.id)
        db_guild.welcome_message = welcome_message.content

        logger.info('Changed welcome message for guild {}.'.format(ctx.guild))
        await ctx.send('Successfully set welcome message.')

    @newbie.command('response-message')
    @newbie_enabled
    async def _response_message(self, ctx: Context, *, msg: str = None):
        """
        Set the response message for the server,
        i.e. the message users have to enter to be granted access to the server.

        Parameters:
            - [optional] msg: The response message users will have to enter.
            Defaults to empty,
            n which case this command will explicitly prompt the caller to enter a message.
        """

        if not msg:
            try:
                response_message = await prompt(
                    'Please enter the response message users have to enter '
                    'upon joining the server.',
                    ctx
                )
            except PromptTimeout:
                await ctx.send('Terminating process due to timeout.')
                return

            msg = response_message.content

        db_guild = ctx.session.query(NewbieGuild).get(ctx.guild.id)
        db_guild.response_message = msg

        # TODO: Edit already sent messages

        logger.info('Changed response message for guild {}.'.format(ctx.guild))
        await ctx.send('Successfully set response message.')

    @newbie.group()
    async def channels(self, ctx: Context):
        """
        Modify the channels unconfirmed users can access.
        """

        if ctx.invoked_subcommand is None:
            await ctx.send(
                'Invalid subcommand passed, please refer to `{}help {}` for further information.\n'
                'Valid options include `add`, `remove` and `list`.'
                .format(clean_prefix(ctx), ctx.command.qualified_name))
            return

    @channels.command()
    @newbie_enabled
    async def add(self, ctx: Context, *, channel: discord.TextChannel = None):
        """
        Add a channel to the list of channels unconfirmed users can access.

        Parameters:
            - [optional] channel: The channel to add to the list,
            identified by mention, ID, or name.
            Defaults to the current channel.
        """

        if not channel:
            channel = ctx.channel

        if not channel.guild.id == ctx.guild.id:
            await ctx.send('The provided channel is not on this server.')
            return

        if ctx.session.query(NewbieChannel).get(channel.id):
            await ctx.send('This channel is already visible to unconfirmed users.')
            return

        everyone_role = ctx.guild.default_role
        everyone_overwrite = channel.overwrites_for(everyone_role)
        everyone_overwrite.update(read_messages=True, read_message_history=True)
        await channel.set_permissions(everyone_role, overwrite=everyone_overwrite)

        db_channel = NewbieChannel(channel_id=channel.id, guild_id=ctx.guild.id)
        ctx.session.add(db_channel)

        logger.info('Added channel {} to visble channels for {}.'.format(channel, ctx.guild))
        await ctx.send('{} is now visible to unconfirmed users.'.format(channel.mention))

    @channels.command()
    @newbie_enabled
    async def remove(self, ctx: Context, *, channel: discord.TextChannel = None):
        """
        Remove a channel from the list of channels unconfirmed users can access.

        Parameters:
            - [optional] channel: The channel to remove from the list,
            identified by mention, ID, or name. Defaults to the current channel.
        """

        if not channel:
            channel = ctx.channel

        if not channel.guild.id == ctx.guild.id:
            await ctx.send('The provided channel is not on this server.')
            return

        db_channel = ctx.session.query(NewbieChannel).get(channel.id)
        if not db_channel:
            await ctx.send('The provided channel is not visible to unconfirmed members.')
            return

        everyone_role = ctx.guild.default_role
        everyone_overwrite = channel.overwrites_for(everyone_role)
        everyone_overwrite.update(read_messages=None, read_message_history=None)
        await channel.set_permissions(everyone_role, overwrite=everyone_overwrite)

        ctx.session.delete(db_channel)

        logger.info('Removed channel {} from visble channels for {}.'.format(channel, ctx.guild))
        await ctx.send('{} is now invisible to unconfirmed users.'.format(channel.mention))

    @channels.command()
    @newbie_enabled
    async def list(self, ctx: Context):
        """
        Lists the channels visible to unconfirmed users of this server.
        """

        answer = 'The following channels are visible to unconfirmed users of this server.```'
        q = ctx.session.query(NewbieChannel)\
            .filter(NewbieChannel.guild_id == ctx.guild.id)
        for db_channel in q:
            channel = ctx.guild.get_channel(db_channel.channel_id)
            if channel:
                answer += '#'
                answer += channel.name
                answer += '\n'

        answer += '```'

        await ctx.send(answer)
