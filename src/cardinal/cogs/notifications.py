from string import Template

from discord import Guild, Member, User
from discord.ext.commands import Cog

from ..db import Notification, NotificationKind


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
