from logging import getLogger

from discord import Embed, Role
from discord.ext.commands import (
    Cog,
    bot_has_permissions,
    group,
    guild_only,
    has_permissions,
)

from ..checks import channel_whitelisted
from ..context import Context
from ..db import JoinRole
from ..utils import clean_prefix

logger = getLogger(__name__)


class Roles(Cog):
    @group("role", aliases=["roles"])
    @guild_only()
    @bot_has_permissions(manage_roles=True)
    @channel_whitelisted()
    async def roles(self, ctx: Context):
        """
        Join, leave and manage roles.

        Required context: Server, whitelisted channel

        Required permissions: None

        Required bot permissions:
            - Manage Roles
        """

        if ctx.invoked_subcommand is None:
            await ctx.send(
                'Invalid command passed. Possible choices are "join", "leave",... \n'
                f"Please refer to `{clean_prefix(ctx)}help {ctx.command.qualified_name}` "
                "for further information."
            )
            return

    @roles.command()
    async def join(self, ctx: Context, *, role: Role):
        """
        Add the user to the specified role.

        Parameters:
            - role: The role to join, identified by mention, ID, or name.
            Must be marked as joinable.
        """

        if not ctx.session.query(JoinRole).get(role.id):
            await ctx.send(f'Role "{role}" is not marked as a joinable role.')
            return

        await ctx.author.add_roles(role, reason="User joined role.")

        await ctx.send(f'User {ctx.author.mention} joined role "{role}"')

    @roles.command()
    async def leave(self, ctx: Context, *, role: Role):
        """
        Remove the user from the specified role.

        Parameters:
            - role: The role to leave, identified by mention, ID, or name.
            Must be marked as joinable.
        """

        if not ctx.session.query(JoinRole).get(role.id):
            await ctx.send(f'Role "{role}" cannot be left through this bot.')
            return

        await ctx.author.remove_roles(role, reason="User left role.")

        await ctx.send(f'User {ctx.author.mention} left role "{role}"')

    @roles.command("list")
    async def _list(self, ctx: Context):
        """
        List the roles that can be joined through the bot,
        i.e. that have been marked as joinable for the current server.
        """

        q = ctx.session.query(JoinRole).filter_by(guild_id=ctx.guild.id)
        role_iter = filter(None, (ctx.guild.get_role(db_role.role_id) for db_role in q))
        role_list = sorted(role_iter, key=lambda r: r.position, reverse=True)

        answer = "Roles that can be joined through this bot:```\n"

        for role in role_list:
            answer += f"{role}\n"

        answer += "```"

        await ctx.send(answer)

    @roles.command()
    async def stats(self, ctx: Context):
        """
        Display the member count for each role marked as joinable on the current server.
        """

        q = ctx.session.query(JoinRole).filter_by(guild_id=ctx.guild.id)
        role_iter = filter(None, (ctx.guild.get_role(db_role.role_id) for db_role in q))
        role_dict = {
            role: sum(1 for member in ctx.guild.members if role in member.roles)
            for role in role_iter
        }

        em = Embed(title=f"Role stats for {ctx.guild}", color=0x38CBF0)
        for role in sorted(role_dict.keys(), key=lambda r: r.position, reverse=True):
            em.add_field(name=role.name, value=str(role_dict[role]))

        await ctx.send(embed=em)

    @roles.command()
    @has_permissions(manage_roles=True)
    async def add(self, ctx: Context, *, role: Role):
        """
        Mark a role as joinable through this bot.

        Parameters:
            - role: The role to mark as joinable, identified by mention, ID, or name.

        Required permissions:
            - Manage Roles
        """

        if ctx.session.query(JoinRole).get(role.id):
            await ctx.send(f'Role "{role}" is already marked as a joinable role.')
            return

        ctx.session.add(JoinRole(role_id=role.id, guild_id=role.guild.id))

        await ctx.send(f'Marked role "{role}" as joinable.')

    @roles.command()
    @has_permissions(manage_roles=True)
    async def remove(self, ctx: Context, *, role: Role):
        """
        Remove a role from the list of roles joinable through this bot.

        Parameters:
            - role: The role to remove from the list, identified by mention, ID, or name.

        Required permissions:
            - Manage Roles
        """

        db_role = ctx.session.query(JoinRole).get(role.id)

        if not db_role:
            await ctx.send(f'Role "{role}" is not marked as a joinable role')
            return

        ctx.session.delete(db_role)

        logger.info(f"Marked role {role} on guild {ctx.guild} as non-joinable.")
        await ctx.send(f'Removed role "{role}" from list of joinable roles.')

    @roles.command()
    @has_permissions(manage_roles=True)
    async def create(self, ctx: Context, *, rolename: str):
        """
        Create a new role on the current server and mark it as joinable through this bot.

        Parameters:
            - rolename: The name of the role to create.

        Required permissions:
            - Manage Roles
        """

        role = await ctx.guild.create_role(name=rolename)

        ctx.session.add(JoinRole(role_id=role.id, guild_id=role.guild.id))

        logger.info(
            f'Created role "{rolename}" ({role.id}) on guild {ctx.guild} and marked it as joinable.'
        )
        await ctx.send(f'Created role "{rolename}" and marked it as joinable.')

    @roles.command()
    @has_permissions(manage_roles=True)
    async def delete(self, ctx: Context, *, role: Role):
        """
        Delete a role from the current server.

        Parameters:
            - role: The role to delete.

        Required permissions:
            - Manage Roles
        """

        role_db = ctx.session.query(JoinRole).get(role.id)
        if role_db:
            ctx.session.delete(role_db)

        await role.delete()
        logger.info(f"Deleted role {role} on guild {ctx.guild}.")
        await ctx.send(f'Successfully deleted role "{role}".')
