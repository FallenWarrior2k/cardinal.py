import discord.utils
from discord.ext import commands
from cardinal import bot, Session
from .models import Channel
from .utils import *


@bot.group(pass_context=True)
async def channel(ctx):
    if ctx.invoked_subcommand is None:
        await bot.say('Invalid command passed: possible choices are "show", "hide", and "opt_in"(mod only).')
        return

    if ctx.message.server is None:
        await bot.say('Command not available outside of a server.')
        return

    bot.delete_message(ctx.message)


@channel.command(pass_context=True, aliases=['join'])
async def show(ctx, channel: str):
    """Enables a user to access a channel."""
    channel_obj = get_channel(ctx, channel)

    if channel_obj is None:
        await bot.say('Channel not found. Please check the spelling.')
        return

    dbsession = Session()

    channel_db = dbsession.query(Channel).get(channel_obj.id)

    if channel_db:
        role = discord.utils.get(ctx.message.server.roles, id=str(channel_db.roleid))

        try:
            await bot.add_roles(ctx.message.author, role)
        except:
            await bot.say('Could not add role, please consult a moderator or try again.')
    else:
        await bot.say('Channel "%s" is not specified as an opt-in channel.' % channel_obj.name)

@channel.command(pass_context=True, aliases=['leave'])
async def hide(ctx, channel: str):
    """Hides a channel from the user's view."""
    channel_obj = get_channel(ctx, channel)

    if channel_obj is None:
        await bot.say('Channel not found. Please check the spelling.')
        return

    dbsession = Session()

    channel_db = dbsession.query(Channel).get(channel_obj.id)

    if channel_db:
        role = discord.utils.get(ctx.message.server.roles, id=str(channel_db.roleid))

        try:
            await bot.remove_roles(ctx.message.author, role)
        except:
            await bot.say('Could not remove role, please consult a moderator or try again.')
    else:
        await bot.say('Channel "%s" is not specified as an opt-in channel.' % channel_obj.name)

@channel.group(pass_context=True, name='opt-in')
@commands.has_permissions(manage_channels=True)
async def _opt_in(ctx):
    if ctx.invoked_subcommand is None:
        await bot.say('Invalid command passed: possible options are "enable" and "disable".')

@_opt_in.command(pass_context=True)
async def enable(ctx, channel: str = None):
    """Makes a channel opt-in."""
    if channel is None:
        channel_obj = ctx.message.channel
    else:
        channel_obj = get_channel(ctx, channel)

    if channel_obj is None:
        await bot.say('Channel not found. Please check the spelling.')
        return
    else:
        channel_id = channel_obj.id

    dbsession = Session()

    if dbsession.query(Channel).get(channel_id):
        await bot.say('Channel "%s" is already opt-in.' % channel_obj.name)
        return

    try:
        role = await bot.create_role(ctx.message.server, name=channel_obj.name)
        print('Created role: Role(name="%s", id=%s)' % (role.name, role.id))
    except Exception as e:
        await bot.say('Could not make channel "%s" opt-in, please consult the dev or try again.' % channel_obj.name)
        await bot.say('Error while creating role.')
        print(e)
        return

    everyone_role = ctx.message.server.default_role
    overwrite = discord.PermissionOverwrite()
    overwrite.read_messages = False

    try:
        await bot.edit_channel_permissions(channel_obj, everyone_role, overwrite)
    except:
        await bot.say('Could not make channel "%s" opt-in, please consult the dev or try again' % channel_obj.name)
        await bot.say('Error while overriding everyone permissions.')
        return

    overwrite.read_messages = True
    try:
        await bot.edit_channel_permissions(channel_obj, role, overwrite)
    except:
        await bot.say('Could not make channel "%s" opt-in, please consult the dev or try again' % channel_obj.name)
        await bot.say('Error while overriding permissions for role members.')

        try:
            bot.edit_channel_permissions(channel_obj, everyone_role, overwrite)
        except:
            await bot.say('Could not unhide the channel. Please do so manually.')

        return

    channel_db = Channel(channelid=channel_obj.id, roleid=role.id)
    dbsession.add(channel_db)
    dbsession.commit()
    await bot.say('Opt-in enabled for channel "%s".' % channel_obj.name)

@_opt_in.command(pass_context=True)
async def disable(ctx, channel: str = None):
    """Removes a channel's opt-in attribute"""
    if channel is None:
        channel_obj = ctx.message.channel
    else:
        channel_obj = get_channel(ctx, channel)

    if channel_obj is None:
        await bot.say('Channel not found. Please check the spelling.')
        return
    else:
        channel_id = channel_obj.id

    dbsession = Session()

    channel_db = dbsession.query(Channel).get(channel_id)

    if channel_db:
        role = discord.utils.get(ctx.message.server.roles, id=str(channel_db.roleid))

        if role is None:
            await bot.say('Could not find role. Was it already deleted?')

        try:
            await bot.delete_role(ctx.message.server, role)
        except:
            await bot.say('Unable to delete role "%s". Please do so manually.' % role.name)

        everyone_role = ctx.message.server.default_role
        overwrite = discord.PermissionOverwrite()
        overwrite.read_messages = True

        try:
            await bot.edit_channel_permissions(channel_obj, everyone_role, overwrite)
        except:
            await bot.say('Could not remove opt-in attribute from channel "%s", please consult the dev or try again.' % channel_obj.name)
            await bot.say('Unable to unhide channel "%s". Please do so manually.' % channel_obj.name)

        dbsession.delete(channel_db)
        dbsession.commit()
        await bot.say('Opt-in disabled for channel "%s".' % channel_obj.name)
    else:
        await bot.say('Channel "%s" is not opt-in' % channel_obj.name)