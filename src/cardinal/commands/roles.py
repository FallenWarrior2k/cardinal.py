import logging
import discord
import discord.ext.commands as commands

from cardinal.commands import Cog
from cardinal.db import Session
from cardinal.db.roles import Role
from cardinal.utils import clean_prefix, channel_whitelisted

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class Roles(Cog):

    def __init__(self, bot):
        super().__init__(bot)

    @commands.group(name='role', pass_context=True, no_pm=True)
    @channel_whitelisted()
    async def roles(self, ctx):
        """Provides functionality for managing roles."""
        if ctx.invoked_subcommand is None:
            await self.bot.say('Invalid command passed. Possible choices are "join", "leave",... \nPlease refer to `{prefix}help {command}` for further information.'
                               .format(prefix=clean_prefix(ctx), command=ctx.invoked_with))
            return

    @roles.command(pass_context=True)
    async def join(self, ctx, *, role: discord.Role):
        """Adds the user to the specified role."""
        dbsession = Session()

        if not dbsession.query(Role).get(role.id):
            await self.bot.say('Role "{0}" is not marked as a joinable role.')
            return

        try:
            await self.bot.add_roles(ctx.message.author, role)
        except:
            await self.bot.say('Could not add role, please consult a moderator or try again.')
            return

        await self.bot.say('User {user} joined role "{role}"'.format(user=ctx.message.author.mention, role=role.name))

    @roles.command(pass_context=True)
    async def leave(self, ctx, *, role: discord.Role):
        """Removes the user from the specified role."""
        dbsession = Session()

        if not dbsession.query(Role).get(role.id):
            await self.bot.say('Role "{0}" cannot be left through this bot.')
            return

        try:
            await self.bot.remove_roles(ctx.message.author, role)
        except:
            await self.bot.say('Could not remove role, please consult a moderator or try again.')
            return

        await self.bot.say('User {user} left role "{role}"'.format(user=ctx.message.author.mention, role=role.name))

    @roles.command(pass_context=True)
    async def list(self, ctx):
        """Lists the roles that can be joined through the bot."""
        dbsession = Session()

        role_list = [role.name for role in ctx.message.server.roles if dbsession.query(Role).get(role.id)]

        answer = 'Roles that can be joined through this bot:```\n'

        for role in role_list:
            answer += role
            answer += '\n'

        answer += '```'

        await self.bot.say(answer)

    @roles.command(pass_context=True)
    async def stats(self, ctx):
        """Shows the member count for each role."""
        dbsession = Session()
        role_list = [role for role in ctx.message.server.roles if dbsession.query(Role).get(role.id)]
        role_dict = {}

        for role in role_list:
            role_dict[role.name] = sum(1 for member in ctx.message.server.members if role in member.roles)

        em = discord.Embed(title='Role stats for ' + ctx.message.server.name, color=0x38CBF0)
        for role, count in role_dict.items():
            em.add_field(name=role, value=count)

        await self.bot.say(embed=em)

    @roles.command()
    @commands.has_permissions(manage_roles=True)
    async def add(self, *, role: discord.Role):
        """Marks a role as joinable."""
        try:
            await self.bot.edit_role(role.server, role, mentionable=True)
        except:
            await self.bot.say('Could not make role "{0}" mentionable.'.format(role.name))
            return

        dbsession = Session()

        if dbsession.query(Role).get(role.id):
            await self.bot.say('Role "{0}" is already marked as a joinable role.'.format(role.name))
            return

        dbsession.add(Role(roleid=role.id))
        dbsession.commit()
        await self.bot.say('Marked role "{0}" as joinable.'.format(role.name))

    @roles.command()
    @commands.has_permissions(manage_roles=True)
    async def remove(self, *, role: discord.Role):
        """Removes a role from the list of joinable roles."""
        try:
            await self.bot.edit_role(role.server, role, mentionable=False)
        except:
            await self.bot.say('Could not make role "{0}" non-mentionable.'.format(role.name))
            return

        dbsession = Session()

        role_db = dbsession.query(Role).get(role.id)

        if not role_db:
            await self.bot.say('Role "{0}" is not marked as a joinable role'.format(role.name))
            return

        dbsession.delete(role_db)
        dbsession.commit()
        await self.bot.say('Removed role "{0}" from list of joinable roles.'.format(role.name))

    @roles.command(pass_context=True)
    @commands.has_permissions(manage_roles=True)
    async def create(self, ctx, *, rolename: str):
        """Creates a new role and makes it joinable through the bot."""
        try:
            role = await self.bot.create_role(ctx.message.server, name=rolename, mentionable=True)
        except:
            await self.bot.say('Could not create role "{0}".'.format(rolename))
            return

        dbsession = Session()
        dbsession.add(Role(roleid=role.id))
        dbsession.commit()
        await self.bot.say('Created role "{0}" and marked it as joinable.'.format(rolename))

    @roles.command()
    @commands.has_permissions(manage_roles=True)
    async def delete(self, *, role: discord.Role):
        """Deletes a role."""
        dbsession = Session()

        role_db = dbsession.query(Role).get(role.id)
        if role_db:
            dbsession.delete(role_db)
            dbsession.commit()

        try:
            await self.bot.delete_role(role.server, role)
        except:
            await self.bot.say('Could not delete role "{0}".'.format(role.name))
            return

        await self.bot.say('Successfully deleted role "{0}".'.format(role.name))
