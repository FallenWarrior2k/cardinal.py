import logging

import discord
import discord.ext.commands as commands

from cardinal.commands import Cog
from cardinal.db import session_scope
from cardinal.db.roles import Role
from cardinal.utils import clean_prefix, channel_whitelisted

logger = logging.getLogger(__name__)


class Roles(Cog):
    def __init__(self, bot):
        super().__init__(bot)

    @commands.group('role')
    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
    @channel_whitelisted()
    async def roles(self, ctx: commands.Context):
        """
        Join, leave and manage roles.

        Required context: Server, whitelisted channel

        Required permissions: None

        Required bot permissions:
            - Manage Roles
        """

        if ctx.invoked_subcommand is None:
            await ctx.send(
                'Invalid command passed. Possible choices are "join", "leave",... \nPlease refer to `{}help {}` for further information.'
                .format(clean_prefix(ctx), ctx.command.qualified_name))
            return

    @roles.command()
    async def join(self, ctx: commands.Context, *, role: discord.Role):
        """
        Add the user to the specified role.

        Parameters:
            - role: The role to join, identified by mention, ID, or name. Must be marked as joinable.
        """

        with session_scope() as session:
            if not session.query(Role).get(role.id):
                await ctx.send('Role "{}" is not marked as a joinable role.'.format(role.name))
                return

        await ctx.author.add_roles(role, reason='User joined role.')

        await ctx.send('User {user} joined role "{role}"'.format(user=ctx.author.mention, role=role.name))

    @roles.command()
    async def leave(self, ctx: commands.Context, *, role: discord.Role):
        """
        Remove the user from the specified role.

        Parameters:
            - role: The role to leave, identified by mention, ID, or name. Must be marked as joinable.
        """

        with session_scope() as session:
            if not session.query(Role).get(role.id):
                await ctx.send('Role "{}" cannot be left through this bot.'.format(role.name))
                return

        await ctx.author.remove_roles(ctx.author, reason='User left role.')

        await ctx.send('User {user} left role "{role}"'.format(user=ctx.author.mention, role=role.name))

    @roles.command('list')
    async def _list(self, ctx: commands.Context):
        """
        List the roles that can be joined through the bot, i.e. that have been marked as joinable for the current server.
        """

        with session_scope() as session:
            role_iter = (discord.utils.get(ctx.guild.roles, id=db_role.role_id) for db_role in session.query(Role).filter_by(guild_id=ctx.guild.id))
            role_iter = (role for role in role_iter if role)
            role_list = sorted(role_iter, key=lambda r: r.position)

        answer = 'Roles that can be joined through this bot:```\n'

        for role in role_list:
            answer += role.name
            answer += '\n'

        answer += '```'

        await ctx.send(answer)

    @roles.command()
    async def stats(self, ctx: commands.Context):
        """
        Display the member count for each role marked as joinable on the current server.
        """

        with session_scope() as session:
            role_iter = (discord.utils.get(ctx.guild.roles, id=db_role.id) for db_role in session.query(Role).filter_by(guild_id=ctx.guild.id))
            role_dict = dict((role, sum(1 for member in ctx.guild.members if role in member.roles))
                             for role in role_iter if role)

        em = discord.Embed(title='Role stats for ' + ctx.guild.name, color=0x38CBF0)
        for role in sorted(role_dict.keys(), key=lambda r: r.position):
            em.add_field(name=role.name, value=role_dict[role])

        await ctx.send(embed=em)

    @roles.command()
    @commands.has_permissions(manage_roles=True)
    async def add(self, ctx: commands.Context, *, role: discord.Role):
        """
        Mark a role as joinable through this bot.

        Parameters:
            - role: The role to mark as joinable, identified by mention, ID, or name.

        Required permissions:
            - Manage Roles
        """

        with session_scope() as session:
            if session.query(Role).get(role.id):
                await ctx.send('Role "{}" is already marked as a joinable role.'.format(role.name))
                return

            session.add(Role(role_id=role.id, guild_id=role.guild.id))

        await ctx.send('Marked role "{}" as joinable.'.format(role.name))

    @roles.command()
    @commands.has_permissions(manage_roles=True)
    async def remove(self, ctx: commands.Context, *, role: discord.Role):
        """
        Remove a role from the list of roles joinable through this bot.

        Parameters:
            - role: The role to remove from the list, identified by mention, ID, or name.

        Required permissions:
            - Manage Roles
        """

        with session_scope() as session:
            role_db = session.query(Role).get(role.id)

            if not role_db:
                await ctx.send('Role "{}" is not marked as a joinable role'.format(role.name))
                return

            session.delete(role_db)

        await ctx.send('Removed role "{}" from list of joinable roles.'.format(role.name))

    @roles.command()
    @commands.has_permissions(manage_roles=True)
    async def create(self, ctx: commands.Context, *, rolename: str):
        """
        Create a new role on the current server and mark it as joinable through this bot.

        Parameters:
            - rolename: The name of the role to create.

        Required permissions:
            - Manage Roles
        """

        role = await ctx.guild.create_role(name=rolename)

        with session_scope() as session:
            session.add(Role(role_id=role.id, guild_id=role.guild.id))

        await ctx.send('Created role "{}" and marked it as joinable.'.format(rolename))

    @roles.command()
    @commands.has_permissions(manage_roles=True)
    async def delete(self, ctx: commands.Context, *, role: discord.Role):
        """
        Delete a role from the current server.

        Parameters:
            - role: The role to delete.

        Required permissions:
            - Manage Roles
        """

        with session_scope() as session:
            role_db = session.query(Role).get(role.id)
            if role_db:
                session.delete(role_db)

        await role.delete()
        await ctx.send('Successfully deleted role "{}".'.format(role.name))
