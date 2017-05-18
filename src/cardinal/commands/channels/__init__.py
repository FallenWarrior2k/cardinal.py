import discord.utils
from discord.ext import commands
from cardinal import bot, Session
from cardinal.utils import channel_whitelisted
from .models import Channel


@bot.group(name='channel', pass_context=True)
@channel_whitelisted()
async def channels(ctx):
    """Provides facilities to work with opt-in channels"""
    if ctx.invoked_subcommand is None:
        await bot.say('Invalid command passed: possible choices are "show", "hide", and "opt-in"(mod only).\nPlease refer to `{0.prefix}help {0.command}` for further information'.format(ctx))
        return

    if ctx.message.server is None:
        await bot.say('Command not available outside of a server.')
        return


@channels.command(pass_context=True, aliases=['join'])
async def show(ctx, channel: discord.Channel):
    """Enables a user to access a channel."""

    dbsession = Session()

    channel_db = dbsession.query(Channel).get(channel.id)

    if channel_db:
        role = discord.utils.get(ctx.message.server.roles, id=channel_db.roleid)

        try:
            await bot.add_roles(ctx.message.author, role)
        except:
            await bot.say('Could not add role, please consult a moderator or try again.')

        await bot.say('User {user} joined channel {channel}.'.format(user=ctx.message.author.mention, channel=channel.mention))
    else:
        await bot.say('Channel {0} is not specified as an opt-in channel.'.format(channel.mention))


@channels.command(pass_context=True, aliases=['leave'])
async def hide(ctx, channel: discord.Channel = None):
    """Hides a channel from the user's view."""
    if channel is None:
        channel = ctx.message.channel

    dbsession = Session()

    channel_db = dbsession.query(Channel).get(channel.id)

    if channel_db:
        role = discord.utils.get(ctx.message.server.roles, id=channel_db.roleid)

        try:
            await bot.remove_roles(ctx.message.author, role)
        except:
            await bot.say('Could not remove role, please consult a moderator or try again.')

        await bot.say('User {user} left channel {channel}.'.format(user=ctx.message.author.mention, channel=channel_obj.mention))
    else:
        await bot.say('Channel {0} is not specified as an opt-in channel.'.format(channel_obj.name))


@channels.group(pass_context=True, name='opt-in')
@commands.has_permissions(manage_channels=True)
async def _opt_in(ctx):
    """Allows moderators to toggle a channel's opt-in status."""
    if ctx.invoked_subcommand is None:
        await bot.say('Invalid command passed: possible options are "enable" and "disable".')


@_opt_in.command(pass_context=True)
async def enable(ctx, channel: discord.Channel = None):
    """Makes a channel opt-in."""
    if channel is None:
        channel = ctx.message.channel

    dbsession = Session()

    if dbsession.query(Channel).get(channel.id):
        await bot.say('Channel {0} is already opt-in.'.format(channel.mention))
        return

    try:
        role = await bot.create_role(ctx.message.server, name=channel.name)
    except:
        await bot.say('Could not make channel {0} opt-in, please consult the dev or try again.'.format(channel.mention))
        await bot.say('Error while creating role.')
        return

    everyone_role = ctx.message.server.default_role
    overwrite = discord.PermissionOverwrite()
    overwrite.read_messages = False

    try:
        await bot.edit_channel_permissions(channel, everyone_role, overwrite)
    except:
        await bot.say('Could not make channel {0} opt-in, please consult the dev or try again'.format(channel.mention))
        await bot.say('Error while overriding everyone permissions.')
        return

    overwrite.read_messages = True
    try:
        await bot.edit_channel_permissions(channel, role, overwrite)
    except:
        await bot.say('Could not make channel {0} opt-in, please consult the dev or try again'.format(channel.mention))
        await bot.say('Error while overriding permissions for role members.')

        try:
            await bot.edit_channel_permissions(channel, everyone_role, overwrite)
        except:
            await bot.say('Could not unhide the channel. Please do so manually.')

        return

    channel_db = Channel(channelid=channel.id, roleid=role.id)
    dbsession.add(channel_db)
    dbsession.commit()
    await bot.say('Opt-in enabled for channel {0}.' .format(channel.mention))


@_opt_in.command(pass_context=True)
async def disable(ctx, channelname: discord.Channel = None):
    """Removes a channel's opt-in attribute"""
    if channel is None:
        channel = ctx.message.channel

    dbsession = Session()

    channel_db = dbsession.query(Channel).get(channel.id)

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
            await bot.edit_channel_permissions(channel, everyone_role, overwrite)
        except:
            await bot.say('Could not remove opt-in attribute from channel {0}, please consult the dev or try again.'.format(channel.mention))
            await bot.say('Unable to unhide channel {0}. Please do so manually.'.format(channel.mention))

        dbsession.delete(channel_db)
        dbsession.commit()
        await bot.say('Opt-in disabled for channel {0}.'.format(channel.mention))
    else:
        await bot.say('Channel {0} is not opt-in'.format(channel.mention))