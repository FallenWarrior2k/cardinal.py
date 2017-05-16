import discord.utils
from discord.ext import commands
from cardinal import bot, Session
from cardinal.utils import get_channel_by_name, channel_whitelisted
from .models import Channel


@bot.group(pass_context=True)
@channel_whitelisted()
async def channel(ctx):
    """Provides facilities to work with opt-in channels"""
    if ctx.invoked_subcommand is None:
        await bot.say('Invalid command passed: possible choices are "show", "hide", and "opt-in"(mod only).\nPlease refer to `{0.prefix}help {0.command}` for further information'.format(ctx))
        return

    if ctx.message.server is None:
        await bot.say('Command not available outside of a server.')
        return


@channel.command(pass_context=True, aliases=['join'])
async def show(ctx, channelname: str):
    """Enables a user to access a channel."""
    channel_obj = get_channel_by_name(ctx, channelname)

    if channel_obj is None:
        await bot.say('Channel "{0}" not found. Please check the spelling.'.format(channelname))
        return

    dbsession = Session()

    channel_db = dbsession.query(Channel).get(channel_obj.id)

    if channel_db:
        role = discord.utils.get(ctx.message.server.roles, id=channel_db.roleid)

        try:
            await bot.add_roles(ctx.message.author, role)
        except:
            await bot.say('Could not add role, please consult a moderator or try again.')

        await bot.say('User {user} joined channel "{channel}".'.format(user=ctx.message.author.mention, channel=channel_obj.name))
    else:
        await bot.say('Channel "{0}" is not specified as an opt-in channel.'.format(channel_obj.name))


@channel.command(pass_context=True, aliases=['leave'])
async def hide(ctx, channelname: str):
    """Hides a channel from the user's view."""
    channel_obj = get_channel_by_name(ctx, channelname)

    if channel_obj is None:
        await bot.say('Channel "{0}" not found. Please check the spelling.'.format(channelname))
        return

    dbsession = Session()

    channel_db = dbsession.query(Channel).get(channel_obj.id)

    if channel_db:
        role = discord.utils.get(ctx.message.server.roles, id=channel_db.roleid)

        try:
            await bot.remove_roles(ctx.message.author, role)
        except:
            await bot.say('Could not remove role, please consult a moderator or try again.')

        await bot.say('User {user} left channel "{channel}".'.format(user=ctx.message.author.mention, channel=channel_obj.name))
    else:
        await bot.say('Channel "{0}" is not specified as an opt-in channel.'.format(channel_obj.name))


@channel.group(pass_context=True, name='opt-in')
@commands.has_permissions(manage_channels=True)
async def _opt_in(ctx):
    """Allows moderators to toggle a channel's opt-in status."""
    if ctx.invoked_subcommand is None:
        await bot.say('Invalid command passed: possible options are "enable" and "disable".')


@_opt_in.command(pass_context=True)
async def enable(ctx, channelname: str = None):
    """Makes a channel opt-in."""
    if channelname is None:
        channel_obj = ctx.message.channel
    else:
        channel_obj = get_channel_by_name(ctx, channelname)

    if channel_obj is None:
        await bot.say('Channel "{0}" not found. Please check the spelling.'.format(channelname))
        return
    else:
        channel_id = channel_obj.id

    dbsession = Session()

    if dbsession.query(Channel).get(channel_id):
        await bot.say('Channel "{0}" is already opt-in.'.format(channel_obj.name))
        return

    try:
        role = await bot.create_role(ctx.message.server, name=channel_obj.name)
        print('Created role: Role(name="{0.name}", id="{0.id}")'.format(role))
    except:
        await bot.say('Could not make channel "{0}" opt-in, please consult the dev or try again.'.format(channel_obj.name))
        await bot.say('Error while creating role.')
        return

    everyone_role = ctx.message.server.default_role
    overwrite = discord.PermissionOverwrite()
    overwrite.read_messages = False

    try:
        await bot.edit_channel_permissions(channel_obj, everyone_role, overwrite)
    except:
        await bot.say('Could not make channel "{0}" opt-in, please consult the dev or try again'.format(channel_obj.name))
        await bot.say('Error while overriding everyone permissions.')
        return

    overwrite.read_messages = True
    try:
        await bot.edit_channel_permissions(channel_obj, role, overwrite)
    except:
        await bot.say('Could not make channel "{0}" opt-in, please consult the dev or try again'.format(channel_obj.name))
        await bot.say('Error while overriding permissions for role members.')

        try:
            await bot.edit_channel_permissions(channel_obj, everyone_role, overwrite)
        except:
            await bot.say('Could not unhide the channel. Please do so manually.')

        return

    channel_db = Channel(channelid=channel_obj.id, roleid=role.id)
    dbsession.add(channel_db)
    dbsession.commit()
    await bot.say('Opt-in enabled for channel "{0}".' .format(channel_obj.name))


@_opt_in.command(pass_context=True)
async def disable(ctx, channelname: str = None):
    """Removes a channel's opt-in attribute"""
    if channelname is None:
        channel_obj = ctx.message.channel
    else:
        channel_obj = get_channel_by_name(ctx, channelname)

    if channel_obj is None:
        await bot.say('Channel not found. Please check the spelling.')
        return
    else:
        channel_id = channel_obj.id

    dbsession = Session()

    channel_db = dbsession.query(Channel).get(channel_id)

    if channel_db:
        role = discord.utils.get(ctx.message.server.roles, id=channel_db.roleid)

        if role is None:
            await bot.say('Could not find role. Was it already deleted?')
        else:
            try:
                await bot.delete_role(ctx.message.server, role)
            except:
                await bot.say('Unable to delete role "{0}". Please do so manually.'.format(role.name))

        everyone_role = ctx.message.server.default_role
        overwrite = discord.PermissionOverwrite()
        overwrite.read_messages = True

        try:
            await bot.edit_channel_permissions(channel_obj, everyone_role, overwrite)
        except:
            await bot.say('Could not remove opt-in attribute from channel "{0}", please consult the dev or try again.'.format(channel_obj.name))
            await bot.say('Unable to unhide channel "{0}". Please do so manually.'.format(channel_obj.name))

        dbsession.delete(channel_db)
        dbsession.commit()
        await bot.say('Opt-in disabled for channel "{0}".'.format(channel_obj.name))
    else:
        await bot.say('Channel "{0}" is not opt-in'.format(channel_obj.name))