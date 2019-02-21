from asyncio import gather, sleep
from contextlib import contextmanager
from datetime import datetime, timedelta
from itertools import chain
from logging import getLogger

from discord import (
    CategoryChannel, Colour, Forbidden, HTTPException,
    Member, PermissionOverwrite, Role, TextChannel
)
from discord.ext.commands import bot_has_permissions, command, group, guild_only, has_permissions

from ..db import MuteGuild, MuteUser
from ..utils import maybe_send
from .basecog import BaseCog

logger = getLogger(__name__)

units = {
    's': 1,
    'sec': 1,
    'secs': 1,
    'second': 1,
    'seconds': 1,
    'm': 1 * 60,
    'min': 1 * 60,
    'mins': 1 * 60,
    'minute': 1 * 60,
    'minutes': 1 * 60,
    'h': 1 * 60 * 60,
    'hour': 1 * 60 * 60,
    'hours': 1 * 60 * 60,
    'd': 1 * 60 * 60 * 24,
    'day': 1 * 60 * 60 * 24,
    'days': 1 * 60 * 60 * 24
}


def to_timedelta(arg):
    if not arg:
        return None

    arg = arg.lower()
    value = None

    for unit, multiplier in units.items():
        if not arg.endswith(unit):
            continue

        value = arg[:-len(unit)].strip()  # Remove unit and any potential whitespace
        value = float(value) * multiplier
        break

    if value is None:
        value = float(arg.strip())  # Special case: no unit; default to seconds

    if value <= 0:
        raise ValueError("Duration must be strictly positive.")

    return timedelta(seconds=value)


async def init_role(ctx, db_guild=None):
    mute_role = await ctx.guild.create_role(name='Muted',
                                            colour=Colour.red(),
                                            hoist=True,
                                            reason='Initialising mute role.')

    try:
        # Position mute role directly below own top role
        new_position = ctx.me.top_role.position - 1
        await mute_role.edit(position=new_position)

        new_overwrite = PermissionOverwrite(send_messages=False, speak=False)

        # Process all categories before touching specific channels
        # Makes use of permission sync
        await gather(
            *(category.set_permissions(mute_role, overwrite=new_overwrite)
              for category in ctx.guild.categories)
        )

        # Process channels unaffected by sync
        # Note: Individual channel objects aren't updated with the new overwrites
        # Only the channel lists on the guild object are updated

        def is_synced(channel):
            current_overwrite = channel.overwrites_for(mute_role)
            return current_overwrite.send_messages is False and current_overwrite.speak is False

        await gather(
            *(channel.set_permissions(mute_role, overwrite=new_overwrite)
              for channel in chain(ctx.guild.text_channels, ctx.guild.voice_channels)
              if not is_synced(channel))
        )
    except HTTPException as e:
        logger.exception(
            'Setting up mute role for guild {} failed due to HTTP error {}.'
            .format(ctx.guild, e.response.status)
        )

        # Something went wrong, clean up role before re-raising
        await mute_role.delete(reason='Internal error initialising mute role.')
        raise

    if db_guild:
        db_guild.role_id = mute_role.id
    else:
        db_guild = MuteGuild(guild_id=ctx.guild.id, role_id=mute_role.id)
        ctx.session.add(db_guild)

    ctx.session.commit()  # Ensure database entry is created/updated even if later calls fail
    return mute_role


async def unmute_member(member, mute_role, channel=None, *, delay_until=None, delay_delta=None):
    delay_seconds = 0

    if delay_until:
        delay_delta = delay_delta or (delay_until - datetime.utcnow())

    if delay_delta:
        delay_seconds = delay_delta.total_seconds()

    if delay_seconds > 0:
        await sleep(delay_seconds)

    try:
        await member.remove_roles(mute_role, reason='Mute duration ran out.')
    except Forbidden:
        logger.warning(
            'No permission to unmute user {0} ({0.id}) on guild {0.guild} ({0.guild.id}).'
            .format(member)
        )
        return
    except HTTPException as e:
        logger.exception(
            'Failed to unmute user {0} ({0.id}) on guild {0.guild} ({0.guild.id}) '
            'due to HTTP error {1}.'
            .format(member, e.response.status)
        )
        return

    if not channel:
        return

    await maybe_send(channel, 'User {} was unmuted automatically.'.format(member.mention))


class Mute(BaseCog):
    """
    Mute utility commands.
    """

    def __init__(self, bot, check_period=30):
        super().__init__(bot)
        self.check_period = check_period
        self._locks = {}
        self.bot.loop.create_task(self.check_mute_timeouts())

    def _process_guild(self, db_guild):
        guild = self.bot.get_guild(db_guild.guild_id)
        if not guild:
            return

        mute_role = guild.get_role(db_guild.role_id)
        if not mute_role:
            return

        for db_mute in db_guild.mutes:
            member = guild.get_member(db_mute.user_id)
            if not member:
                continue

            yield unmute_member(
                member,
                mute_role,
                guild.get_channel(db_mute.channel_id),
                delay_until=db_mute.muted_until
            )

    def _get_unmutes(self):
        with self.bot.session_scope() as session:
            # Query for mutes that run before the next iteration
            # No need to delete by hand, self.on_guild_member_update() will clean up
            next_iteration_timestamp = (datetime.utcnow() + timedelta(seconds=self.check_period))
            q = session.query(MuteGuild) \
                .join(MuteGuild.mutes) \
                .filter(MuteUser.muted_until.isnot(None),
                        next_iteration_timestamp >= MuteUser.muted_until)

            return chain.from_iterable(self._process_guild(db_guild) for db_guild in q)

    async def check_mute_timeouts(self):
        await self.bot.wait_until_ready()

        while True:
            unmutes = self._get_unmutes()
            await gather(*unmutes)
            await sleep(self.check_period)

    @BaseCog.listener()
    async def on_guild_channel_create(self, channel):
        with self.bot.session_scope() as session:
            db_guild = session.query(MuteGuild).get(channel.guild.id)
            if not db_guild:
                return

            mute_role = channel.guild.get_role(db_guild.role_id)
            if not mute_role:
                return

            if isinstance(channel, CategoryChannel):
                await channel.set_permissions(mute_role, send_messages=False, speak=False)
            elif isinstance(channel, TextChannel):
                await channel.set_permissions(mute_role, send_messages=False)
            else:
                await channel.set_permissions(mute_role, speak=False)

    @BaseCog.listener()
    async def on_guild_role_delete(self, role):
        with self.bot.session_scope() as session:
            # Delete any bindings if the corresponding role is deleted
            # Use Query.delete() to prevent redundant SELECT
            # Role ID is indexed so delete is faster than querying by guild ID and comparing
            session.query(MuteGuild).filter_by(role_id=role.id).delete(synchronize_session=False)

    @BaseCog.listener()
    async def on_member_join(self, member):
        with self.bot.session_scope() as session:
            db_mute = session.query(MuteUser).get((member.id, member.guild.id))

            # Do not re-mute if mute should have run out already
            # Leave cleanup to self.check_mute_timeouts()
            if not db_mute or db_mute.muted_until <= datetime.utcnow():
                return

            role = member.guild.get_role(db_mute.guild.role_id)
            if not role:
                return

            # Re-mute people who left while muted
            await member.add_roles(role, reason='Muted member rejoined')

    @BaseCog.listener()
    async def on_member_update(self, before, after):
        with self.bot.session_scope() as session:
            db_guild = session.query(MuteGuild).get(before.guild.id)
            if not db_guild:
                return

            mute_role = before.guild.get_role(db_guild.role_id)
            if not mute_role:
                return

            roles_before = set(before.roles)
            roles_after = set(after.roles)

            mute_removed = mute_role in (roles_before - roles_after)
            mute_added = mute_role in (roles_after - roles_before)

            db_mute = session.query(MuteUser).get((before.id, before.guild.id))

            if mute_removed and db_mute:
                session.delete(db_mute)

            # Check if binding exists already to prevent double create
            if mute_added and not db_mute:
                db_mute = MuteUser(user_id=before.id, guild_id=before.guild.id)
                session.add(db_mute)

    # Ensure this is neither parsed nor called for anything but the mute command itself
    @group(invoke_without_command=True, aliases=['gag'])
    @guild_only()
    @has_permissions(manage_roles=True)
    @bot_has_permissions(manage_roles=True)
    async def mute(self, ctx, member: Member, *, duration: to_timedelta = None):
        """
        Mute a user from chat, optionally specifying an automatic timeout.
        Does nothing if the user is already muted.

        Arguments:
             - member: Member to mute.
             - [optional] duration: Duration of the mute. Defaults to infinite.
                Default unit if unspecified is seconds.
                Note that it is not possible to explicitly specify infinity as a duration.

        Required context: Server

        Required permissions:
            - Manage Roles

        Required bot permissions:
            - Manage Roles
        """

        db_guild = ctx.session.query(MuteGuild).get(ctx.guild.id)
        mute_role = None
        if db_guild:
            mute_role = ctx.guild.get_role(db_guild.role_id)

        if not mute_role:
            # No role => create new and save to DB
            mute_role = await init_role(ctx, db_guild)

        if mute_role in member.roles:  # Mute role already there, nothing to do here
            return

        # Add mute to DB prior to role assigment, member update handler triggers otherwise
        is_short_mute = duration and duration.total_seconds() <= self.check_period
        if not is_short_mute:
            db_mute = MuteUser(user_id=member.id, guild_id=ctx.guild.id)
            if duration:
                db_mute.muted_until = datetime.utcnow() + duration
                db_mute.channel_id = ctx.channel.id

            ctx.session.add(db_mute)
            ctx.session.commit()  # Necessary to prevent race condition with event handler

        await member.add_roles(mute_role, reason='Muted by {}.'.format(ctx.author))

        # TODO: Include duration in message
        await maybe_send(ctx, 'User {} was muted by {}.'.format(member.mention, ctx.author.mention))

        # User should be muted for less than one check period
        # => queue unmute directly and don't touch DB from here
        if is_short_mute:
            await unmute_member(member, mute_role, ctx.channel, delay_delta=duration)

    @mute.command()
    @guild_only()
    @has_permissions(manage_roles=True)
    async def setrole(self, ctx, role: Role):
        """
        Set the mute role to use with mute commands and mute detection.
        Setting it via this command overwrites any existing role.

        However, this command does NOT touch permissions in any way.
        Instead, it assumes you have already set up the role's permissions in a satisfactory manner.

        If the new role is the same as the old one, this command has no effect.

        Internally, this unmarks those previously marked as muted if they do not have the new role.
        Inversely, it marks everyone having the new role as muted.

        Required context: Server

        Required permissions:
            - Manage Roles
        """

        db_guild = ctx.session.query(MuteGuild).get(ctx.guild.id)
        if not db_guild:
            db_guild = MuteGuild(guild_id=ctx.guild.id, role_id=role.id)
            ctx.session.add(db_guild)
            return

        if db_guild.role_id == role.id:
            return

        # Remove usages of old role from DB
        role_member_ids = {member.id for member in role.members}  # Set for later use
        ctx.session.query(MuteUser).filter(
            MuteUser.guild_id == ctx.guild.id,
            MuteUser.user_id.notin_(list(role_member_ids))  # Make list because SQLAlchemy wants one
        ).delete(synchronize_session=False)

        # Query remaining mutes
        existing_db_mute_ids = {
            db_mute.user_id
            for db_mute in ctx.session.query(MuteUser).filter_by(guild_id=ctx.guild.id)
        }
        # Make set with members that need to be added to DB
        new_mute_member_ids = role_member_ids - existing_db_mute_ids
        ctx.session.add_all(
            MuteUser(user_id=member_id, guild_id=ctx.guild.id) for member_id in new_mute_member_ids
        )

    @command()
    @guild_only()
    @has_permissions(manage_roles=True)
    @bot_has_permissions(manage_roles=True)
    async def unmute(self, ctx, member: Member):
        """
        Unmute a user. Does nothing if the user is not muted.

        Required context: Server

        Required permissions:
            - Manage Roles

        Required bot permissions:
            - Manage Roles
        """

        db_mute = ctx.session.query(MuteUser).get((member.id, ctx.guild.id))
        if not db_mute:
            return

        db_guild = db_mute.guild
        mute_role = ctx.guild.get_role(db_guild.role_id)
        if not mute_role:
            return

        # No need to manually delete DB row, member update handler will
        await member.remove_roles(mute_role, reason='Explicit unmute by {}.'.format(ctx.author))
        await maybe_send(
            ctx,
            'User {} was unmuted by {}.'.format(member.mention, ctx.author.mention)
        )
