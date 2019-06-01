import re
from asyncio import sleep
from datetime import datetime, timedelta
from functools import partial, wraps
from logging import getLogger

from discord import Forbidden, HTTPException, Member, Message, Permissions, TextChannel
from discord.abc import PrivateChannel
from discord.ext.commands import Command, bot_has_permissions, group, guild_only, has_permissions
from discord.utils import get

from ..context import Context
from ..db import NewbieChannel, NewbieGuild, NewbieUser
from ..errors import PromptTimeout
from ..utils import clean_prefix, prompt
from .basecog import BaseCog

logger = getLogger(__name__)

# Matches either a channel mention of the form "<#id>" or a raw ID.
# The actual ID can be extracted from the 'id' group of the match object
channel_re = re.compile(r'((<#)|^)(?P<id>\d+)(?(2)>|(\s|$))')


def newbie_enabled(func):
    """Decorator to check if newbie roling is enabled before running the command."""

    if isinstance(func, Command):
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

    if isinstance(func, Command):
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
                        logger.info(f'Kicked overdue user {member} from guild {guild}.')
                    except Forbidden:
                        logger.exception(
                            f'Lacking permissions to kick user {member} from guild {guild}.'
                        )
                    except HTTPException as e:
                        logger.exception(
                            f'Failed to kick user {member} from guild {guild} '
                            f'due to HTTP error {e.response.status}.'
                        )

            await sleep(60)

    @staticmethod
    async def add_member(session, db_guild: NewbieGuild, member: Member):
        if session.query(NewbieUser).get((member.id, db_guild.guild_id)):
            return  # Exit if user already in DB

        message_content = db_guild.welcome_message

        message_content += '\n'
        message_content += f'Please reply with the following message to be granted access to ' \
            f'"{member.guild}".\n'
        message_content += f'```{db_guild.response_message}```'

        try:
            message = await member.send(message_content)
        except Forbidden:
            logger.exception(
                f'Cannot message user {member} and thus cannot prompt for verification.'
            )
            return
        except HTTPException as e:
            logger.exception(
                f'Failed sending message to user {member} due to HTTP error {e.response.status}.'
            )
            return
        else:
            # Use utcnow() instead of join time to treat members who got the message too late fairly
            db_user = NewbieUser(guild_id=member.guild.id,
                                 user_id=member.id,
                                 message_id=message.id,
                                 joined_at=datetime.utcnow())
            session.add(db_user)
            session.commit()
            logger.info('Added new user {0} to database for guild {0.guild}.'.format(member))

            try:
                # Necessary in compliance with Discord's latest ToS changes ¯\_(ツ)_/¯
                await member.send(
                    f'Please note that by staying on "{member.guild}", '
                    'you agree that this bot stores your user ID for identification purposes.\n'
                    'It shall be deleted once you confirm the above message or leave the server.'
                )
            except HTTPException:
                # First message went through, no need to further handle this, should it ever occur
                pass

    @BaseCog.listener()
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

    @BaseCog.listener()
    async def on_member_join(self, member: Member):
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

    @BaseCog.listener()
    async def on_member_remove(self, member: Member):
        with self.bot.session_scope() as session:
            # Necessary in compliance with Discord's latest ToS changes ¯\_(ツ)_/¯
            # Use query instead of object deletion to prevent redundant SELECT query
            session.query(NewbieUser)\
                .filter(NewbieUser.user_id == member.id, NewbieUser.guild_id == member.guild.id)\
                .delete(synchronize_session=False)

    @BaseCog.listener()
    async def on_member_update(self, before: Member, after: Member):
        with self.bot.session_scope() as session:
            db_user = session.query(NewbieUser).get((before.id, before.guild.id))

            if not db_user:
                return

            role = before.guild.get_role(db_user.guild.role_id)

            if not role:
                return

            if role not in before.roles and role in after.roles:
                session.delete(db_user)

    @BaseCog.listener()
    async def on_message(self, msg: Message):
        if msg.author.id == self.bot.user.id:
            return

        if not isinstance(msg.channel, PrivateChannel):
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
                        except Forbidden:
                            logger.exception(
                                'Lacking permissions to kick user {0} from guild {0.guild}.'
                                .format(member)
                            )
                        except HTTPException as e:
                            logger.exception(
                                'Failed to kick user {0} from guild {0.guild} '
                                'due to HTTP error {1}.'
                                .format(member, e.response.status)
                            )
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
                    logger.info('Verified user {0} on guild {0.guild}.'.format(member))

                    await msg.author.send(f'Welcome to {guild}')
                except Forbidden:
                    logger.exception(
                        'Lacking permissions to manage roles for '
                        'user {0} on guild {0.guild}.'.format(member)
                    )
                except HTTPException as e:
                    logger.exception(
                        'Failed to manage roles for user {0} on guild {0.guild} '
                        'due to HTTP error {1}.'
                        .format(member, e.response.status)
                    )

    @group()
    @guild_only()
    @has_permissions(manage_guild=True)
    @bot_has_permissions(manage_roles=True, manage_channels=True)
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
                f'Invalid subcommand passed, please refer to '
                f'`{clean_prefix(ctx)}help {ctx.command.qualified_name}` for further information.'
            )

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
        member_permissions = Permissions(0x400 | 0x800 | 0x10000)

        bound_prompt = partial(prompt, ctx=ctx)

        try:
            channels_message = await bound_prompt(
                'Please enter the channels that are to remain visible to newbies, '
                'separated by spaces.\n_Takes channel mentions, names, and IDs._'
            )

            welcome_message = await bound_prompt(
                'Enter the welcome message that should be displayed to new users.'
            )

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
                channel = get(ctx.guild.text_channels, name=channel_string.lower())

            if channel and channel.guild.id == ctx.guild.id:
                everyone_overwrite = channel.overwrites_for(everyone_role)
                everyone_overwrite.update(read_messages=True, read_message_history=True)
                await channel.set_permissions(everyone_role, overwrite=everyone_overwrite)
                db_channel = NewbieChannel(channel_id=channel.id, guild_id=ctx.guild.id)
                ctx.session.add(db_channel)

        logger.info(f'Enabled newbie roling on guild {ctx.guild}.')
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
        merged_perms = Permissions(everyone_perms.value)
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

        logger.info(f'Disabled newbie roling on guild {ctx.guild}.')
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

        logger.info(f'Changed timeout for {ctx.guild} to {delay} hours.')
        await ctx.send(f'Successfully set timeout to {delay} hours.')

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

        logger.info(f'Changed welcome message for guild {ctx.guild}.')
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

        logger.info(f'Changed response message for guild {ctx.guild}.')
        await ctx.send('Successfully set response message.')

    @newbie.group()
    async def channels(self, ctx: Context):
        """
        Modify the channels unconfirmed users can access.
        """

        if ctx.invoked_subcommand is None:
            await ctx.send(
                'Invalid subcommand passed, please refer to '
                f'`{clean_prefix(ctx)}help {ctx.command.qualified_name}` '
                'for further information.\nValid options include `add`, `remove` and `list`.'
            )
            return

    @channels.command()
    @newbie_enabled
    async def add(self, ctx: Context, *, channel: TextChannel = None):
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

        logger.info(f'Added channel {channel} to visble channels for {ctx.guild}.')
        await ctx.send(f'{channel.mention} is now visible to unconfirmed users.')

    @channels.command()
    @newbie_enabled
    async def remove(self, ctx: Context, *, channel: TextChannel = None):
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

        logger.info(f'Removed channel {channel} from visble channels for {ctx.guild}.')
        await ctx.send(f'{channel.mention} is now invisible to unconfirmed users.')

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
                answer += f'#{channel.name}\n'

        answer += '```'

        await ctx.send(answer)
