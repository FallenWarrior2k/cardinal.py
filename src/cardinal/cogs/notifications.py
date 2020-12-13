from string import Template
from typing import Optional

from discord import Guild, Member, TextChannel, User
from discord.ext.commands import Cog, Greedy, group, guild_only, has_permissions

from ..db import Notification, NotificationKind
from ..utils import maybe_send


class Notifications(Cog):
    def __init__(self, scoped_session):
        self._session = scoped_session

    async def _process_event(self, kind: NotificationKind, guild: Guild, user: User):
        db_notif = self._session.query(Notification).get((guild.id, kind))
        if not db_notif:
            return

        channel = guild.get_channel(db_notif.channel_id)
        if not channel:
            return

        template = Template(db_notif.template)
        format_args = {
            "name": user.display_name,
            "fullname": f"{user.name}#{user.discriminator}",
            "mention": user.mention,
            "id": user.id
        }

        await maybe_send(channel, template.safe_substitute(format_args))

    @Cog.listener()
    async def on_member_join(self, member: Member):
        await self._process_event(NotificationKind.JOIN, member.guild, member)

    @Cog.listener()
    async def on_member_remove(self, member: Member):
        # TODO: Maybe don't fire if this is also a ban
        # Potential issue: notifications could be in different channels
        await self._process_event(NotificationKind.LEAVE, member.guild, member)

    @Cog.listener()
    async def on_member_ban(self, guild: Guild, user: User):
        # TODO: Maybe don't fire if ban was by this bot
        # Same potential issues as above
        await self._process_event(NotificationKind.BAN, guild, user)

    @Cog.listener()
    async def on_member_unban(self, guild: Guild, user: User):
        await self._process_event(NotificationKind.UNBAN, guild, user)

    @group(aliases=['greetings', 'joins', 'welcome', 'welcomes'])
    @guild_only()
    @has_permissions(manage_guild=True)
    async def notifications(self, ctx):
        """
        Control a server's join/leave/ban notifications.

        Required context: Server

        Required permissions:
            - Manage Server
        """
        if ctx.invoked_subcommand is None:
            await maybe_send(ctx, 'Invalid subcommand passed. '
                                  'Possible options are "enable", "move", or "disable".')

    @notifications.command()
    async def move(self, ctx, kinds: Greedy[NotificationKind] = list(NotificationKind), channel: TextChannel = None):
        """
        Move one or more notification kinds to the specified channel.
        Defaults to moving all kinds to the current channel.

        Arguments:
            - [optional, list] kinds: Notification kinds to move.
                Not enabled ones are ignored.
            - [optional] channel: Channel to move notifications to.
                Can be specified without specifying any kinds.
        """
        channel = channel or ctx.channel
        # Dedupe kinds, but keep list type for SQLA in_ operator
        kinds = list(set(kinds))

        num_moved = self._session.query(Notification).filter(
            Notification.guild_id == ctx.guild.id,
            Notification.kind.in_(kinds)
        ).update({Notification.channel_id: channel.id}, synchronize_session=False)
        self._session.commit()

        await maybe_send(ctx, f"Moved {num_moved} notification kind{'' if num_moved == 1 else 's'} to {channel.mention}.")
