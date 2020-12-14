from string import Template
from typing import Optional

from discord import Guild, Member, TextChannel, User
from discord.ext.commands import Cog, Greedy, group, guild_only, has_permissions

from ..db import Notification, NotificationKind
from ..errors import PromptTimeout
from ..utils import maybe_send, prompt

_DEFAULT_TEMPLATES = {
    NotificationKind.JOIN: "Welcome to the server, $mention.",
    NotificationKind.LEAVE: "$fullname has left the server.",
    NotificationKind.BAN: "$fullname has been banned.",
    NotificationKind.UNBAN: "$fullname has been unbanned."
}


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

    async def _bind_notifications(
        self,
        ctx,
        channel: TextChannel,
        kind: NotificationKind,
        # Regular function (not a command), so using optional like this is fine
        template: Optional[str]
    ):
        template = template or _DEFAULT_TEMPLATES[kind]
        kind_str = kind.lower()
        channel_str = "this channel" if channel == ctx.channel else channel.mention

        # TODO: Replace this with an assignment expression after switching to Python 3.8
        db_notif = self._session.query(Notification).get((ctx.guild.id, kind))
        if db_notif:
            old_channel = ctx.guild.get_channel(db_notif.channel_id)
            move = False
            try:
                resp_msg = await prompt(
                    f"Notifications for the {kind_str} event are currently bound to {old_channel.mention}. "
                    f"Move to {channel_str}? [y/n]",
                    ctx
                )
            except PromptTimeout:
                await maybe_send(ctx, "Aborting due to timeout.")
                return

            resp = resp_msg.content.lower()
            if resp == "y":
                db_notif.channel_id = ctx.channel.id
            elif resp == "n":
                return
            else:
                await maybe_send(ctx, "Invalid response. Assuming no.")
                return
        else:
            db_notif = Notification(
                guild_id=ctx.guild.id,
                kind=kind,
                channel_id=channel.id,
                template=template
            )
            self._session.add(db_notif)

        # I know committing in a loop is bad, but we have at most 4 iterations with 1 insert/update max. each
        # One commit at the end (begin_nested() or not) would've been annoying af wrt error handling
        self._session.commit()
        await maybe_send(ctx, f"Bound notifications for the {kind_str} event to {channel_str}.")

    @notifications.command()
    async def enable(
        self,
        ctx,
        channel: Optional[TextChannel] = None,
        kinds: Greedy[NotificationKind] = list(NotificationKind),
        *,
        template: str = None
    ):
        """
        Enable one or more notification kinds in the given channel.
        Passing no template starts an interactive setup process.

        Arguments:
            - [optional] channel: Channel to send notifications to.
                Defaults to the current channel.
            - [optional, list] kind: Notification kinds to enable.
                Choice of "join", "leave", "ban", or "unban". Case doesn't matter.
                Defaults to all of them.
            - [optional] template: Template to use for the notification.
                You must specify exactly one notification kind when using this.

                These can use several placeholders of the form $placeholder
                or ${placeholder}. The latter form is useful if there are
                directly adjacent characters that might conflict,
                e.g. trying to italicize a name using "_$name_" won't work,
                but "_${name}_" will.
                The available placeholders are as follows:
                    - name: user's nickname if set, username otherwise
                    - fullname: "qualified" username in Name#0000 format
                    - mention: mentions the user
                    - id: numerical user ID

                NB: This parameter is ignored when moving to a different channel.
                Use the move and settemplate commands for that.
        """
        channel = channel or ctx.channel
        # Dedupe, but preserve order to not cause confusion
        kinds = list(dict.fromkeys(kinds))

        # Non-interactive mode
        if template:
            if len(kinds) != 1:
                await maybe_send(
                    ctx,
                    "You must specify exactly one kind of notification when passing a template."
                )
                return

            await self._bind_notifications(ctx, channel, kinds[0], template)
            return

        # Interactive mode starts here
        # Filter client-side because query returns 4 rows max
        # Sending entire channel list to server for filtering would probably be more expensive
        db_notifs = [db_notif
                     for db_notif in self._session.query(Notification).filter_by(guild_id=ctx.guild.id)
                     if ctx.guild.get_channel(db_notif.channel_id)]

        # Exclude alr bound kinds from further setup
        for db_notif in db_notifs:
            kinds.remove(db_notif.kind)

            # Avoid no-op moves
            if db_notif.channel_id != channel.id:
                # Just pass None as the template as it'll never be used anyway
                await self._bind_notifications(ctx, channel, db_notif.kind, None)

        if not kinds:
            await maybe_send(ctx, "Nothing left to set up. Exiting.")
            return

        # Interactive mode starts here, for realz now
        for kind in kinds:
            try:
                resp_msg = await prompt(
                    f"Enter the desired template for the {kind.lower()} event, "
                    f'or "default" to use the default of "{_DEFAULT_TEMPLATES[kind]}".',
                    ctx
                )
            except PromptTimeout:
                await maybe_send("Aborting due to timeout.")
                return

            template = resp_msg.content
            if template.lower() == "default":
                template = _DEFAULT_TEMPLATES[kind]

            await self._bind_notifications(ctx, channel, kind, template)

    @notifications.command()
    async def disable(self, ctx, kinds: Greedy[NotificationKind] = list(NotificationKind)):
        """
        Disable one or more notification kinds.
        Defaults to disabling all of them.
        """
        # Dedupe kinds, but keep list type for SQLA in_ operator
        kinds = list(set(kinds))

        num_deleted = self._session.query(Notification).filter(
            Notification.guild_id == ctx.guild.id,
            Notification.kind.in_(kinds)
        ).delete(synchronize_session=False)
        self._session.commit()

        await maybe_send(ctx, f"Disabled {num_deleted} notification kind{'' if num_deleted == 1 else 's'}.")

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
        # Same as above
        kinds = list(set(kinds))

        num_moved = self._session.query(Notification).filter(
            Notification.guild_id == ctx.guild.id,
            Notification.kind.in_(kinds)
        ).update({Notification.channel_id: channel.id}, synchronize_session=False)
        self._session.commit()

        await maybe_send(ctx, f"Moved {num_moved} notification kind{'' if num_moved == 1 else 's'} to {channel.mention}.")
