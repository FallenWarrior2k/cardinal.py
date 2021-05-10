from logging import getLogger

from discord import Member, NotFound, Object
from discord.ext.commands import (
    BadArgument,
    Cog,
    UserConverter,
    UserNotFound,
    bot_has_permissions,
    command,
    guild_only,
    has_permissions,
)

from ..context import Context

logger = getLogger(__name__)


class _UserOrId(UserConverter):
    async def convert(self, ctx, argument):
        try:
            return await super().convert(ctx, argument)
        except UserNotFound:
            try:
                return Object(argument)
            except TypeError as e:
                raise BadArgument() from e


class Moderation(Cog):
    """
    A collection of general moderation commands to simplify the daily life of a mod.
    """

    @command(aliases=["boot"])
    @guild_only()
    @has_permissions(kick_members=True)
    @bot_has_permissions(kick_members=True)
    async def kick(self, ctx: Context, user: Member, *, reason: str = None):
        """
        Kick a member from the current server.

        Parameters:
            - user: The member to kick, identified by mention, ID, or name.
            Must be a member of the server.
            - [optional] reason: The reason for kicking the user. Defaults to empty.

        Required context: Server

        Required permissions:
            - Kick Members

        Required bot permissions:
            - Kick Members
        """

        await user.kick(reason=reason)
        await ctx.send(
            "User **{0}** ({0.id}) was kicked by {1}.".format(user, ctx.author.mention)
        )

    @command(aliases=["getout", "gulag"])
    @guild_only()
    @has_permissions(ban_members=True)
    @bot_has_permissions(ban_members=True)
    async def ban(
        self, ctx: Context, user: _UserOrId, prune_days: int = 1, *, reason: str = None
    ):
        """
        Ban a user from the current server.

        Parameters:
            - user: The user to ban, identified by mention, ID, or name.
            - [optional] prune_days: The number of days
            for which the user's message should be pruned. Defaults to one day.
            - [optional] reason: The reason for banning the user. Defaults to empty.

        Required context: Server

        Required permissions:
            - Ban Members

        Required bot permissions:
            - Ban Members
        """

        if prune_days < 0:
            prune_days = 0
        elif prune_days > 7:
            prune_days = 7

        try:
            await ctx.guild.ban(user, reason=reason, delete_message_days=prune_days)
        # Undocumented: Discord returns 404 when trying to ban a nonexistent user
        except NotFound:
            await ctx.send("Specified user does not exist.")
        else:
            # This outputs gibberish when user is an Object, but whatever
            await ctx.send(
                "User **{0}** ({0.id}) was banned by {1}.".format(
                    user, ctx.author.mention
                )
            )
