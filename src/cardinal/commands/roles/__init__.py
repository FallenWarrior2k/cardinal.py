import logging
import discord
from discord.ext import commands
from cardinal import bot, Session
from cardinal.utils import channel_whitelisted, clean_prefix
from .models import Role

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@bot.group(name='role', pass_context=True, no_pm=True)
@channel_whitelisted()
async def roles(ctx):
    """Provides functionality for managing roles."""
    if ctx.invoked_subcommand is None:
        await bot.say(f'Invalid command passed. Possible choices are "join", "leave",... \nPlease refer to `{clean_prefix(ctx)}help {ctx.invoked_with}` for further information.')
        return


@roles.command(pass_context=True)
async def join(ctx, role: discord.Role):
    """Adds the user to the specified role."""
    dbsession = Session()

    if not dbsession.query(Role).get(role.id):
        await bot.say('Role "{0}" is not marked as a joinable role.')
        return

    try:
        await bot.add_roles(ctx.message.author, role)
    except:
        await bot.say('Could not add role, please consult a moderator or try again.')
        return

    await bot.say('User {user} joined role "{role}"'.format(user=ctx.message.author.mention, role=role.name))


@roles.command(pass_context=True)
async def leave(ctx, role: discord.Role):
    """Removes the user from the specified role."""
    dbsession = Session()

    if not dbsession.query(Role).get(role.id):
        await bot.say('Role "{0}" cannot be left through this bot.')
        return

    try:
        await bot.remove_roles(ctx.message.author, role)
    except:
        await bot.say('Could not remove role, please consult a moderator or try again.')
        return

    await bot.say('User {user} left role "{role}"'.format(user=ctx.message.author.mention, role=role.name))


@roles.command(pass_context=True)
async def list(ctx):
    """Lists the roles that can be joined through the bot."""
    dbsession = Session()

    role_list = [role.name for role in ctx.message.server.roles if dbsession.query(Role).get(role.id)]

    answer = 'Roles that can be joined through this bot:```\n'

    for role in role_list:
        answer += role
        answer += '\n'

    answer += '```'

    await bot.say(answer)


@roles.command()
@commands.has_permissions(manage_roles=True)
async def add(role: discord.Role):
    """Marks a role as joinable."""
    try:
        await bot.edit_role(role.server, role, mentionable=True)
    except:
        await bot.say('Could not make role "{0}" mentionable.'.format(role.name))
        return

    dbsession = Session()

    if dbsession.query(Role).get(role.id):
        await bot.say('Role "{0}" is already marked as a joinable role.'.format(role.name))
        return

    dbsession.add(Role(roleid=role.id))
    dbsession.commit()
    await bot.say('Marked role "{0}" as joinable.'.format(role.name))


@roles.command()
@commands.has_permissions(manage_roles=True)
async def remove(role: discord.Role):
    """Removes a role from the list of joinable roles."""
    try:
        await bot.edit_role(role.server, role, mentionable=False)
    except:
        await bot.say('Could not make role "{0}" non-mentionable.'.format(role.name))
        return

    dbsession = Session()

    role_db = dbsession.query(Role).get(role.id)

    if not role_db:
        await bot.say('Role "{0}" is not marked as a joinable role'.format(role.name))
        return

    dbsession.delete(role_db)
    dbsession.commit()
    await bot.say('Removed role "{0}" from list of joinable roles.'.format(role.name))


@roles.command(pass_context=True)
@commands.has_permissions(manage_roles=True)
async def create(ctx, rolename: str):
    """Creates a new role and makes it joinable through the bot."""
    try:
        role = await bot.create_role(ctx.message.server, name=rolename, mentionable=True)
    except:
        await bot.say('Could not create role "{0}".'.format(rolename))
        return

    dbsession = Session()
    dbsession.add(Role(roleid=role.id))
    dbsession.commit()
    await bot.say('Created role "{0}" and marked it as joinable.'.format(rolename))


@roles.command()
@commands.has_permissions(manage_roles=True)
async def delete(role: discord.Role):
    """Deletes a role."""
    dbsession = Session()

    role_db = dbsession.query(Role).get(role.id)
    if role_db:
        dbsession.delete(role_db)
        dbsession.commit()

    try:
        await bot.delete_role(role.server, role)
    except:
        await bot.say('Could not delete role "{0}".'.format(role.name))
        return

    await bot.say('Successfully deleted role "{0}".'.format(role.name))