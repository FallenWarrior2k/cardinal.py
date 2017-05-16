from discord.ext import commands
from cardinal import bot, Session
from cardinal.models import WhitelistedChannel
from cardinal.utils import get_channel_by_name


@bot.group(pass_context=True)
@commands.has_permissions(manage_channels=True)
async def whitelist(ctx):
    """Provides functionality for whitelisting channels to allow usage of channel-restricted commands."""
    if ctx.invoked_subcommand is None:
        await bot.say('Invalid command passed. Possible choices are "add" and "remove".\nPlease refer to `{0.prefix}help {0.command}` for further information.'.format(ctx))
        return

@whitelist.command(pass_context=True)
async def add(ctx, channelname: str = None):
    """Adds a channel to the whitelist."""
    if channelname is None:
        channel_obj = ctx.message.channel
    else:
        channel_obj = get_channel_by_name(ctx, channelname)

    if channel_obj is None:
        await bot.say('Channel "{0}" not found. Please check the spelling.'.format(channelname))
        return

    dbsession = Session()

    if dbsession.query(WhitelistedChannel).get(channel_obj.id):
        await bot.say('Channel {0} is already whitelisted.'.format(channel_obj.name))
        return

    channel_db = WhitelistedChannel(channelid=channel_obj.id)
    dbsession.add(channel_db)
    dbsession.commit()
    await bot.say('Whitelisted channel "{0}".'.format(channel_obj.name))

@whitelist.command(pass_context=True)
async def remove(ctx, channelname: str = None):
    """Removes a channel from the whitelist."""
    if channelname is None:
        channel_obj = ctx.message.channel
    else:
        channel_obj = get_channel_by_name(ctx, channelname)

    if channel_obj is None:
        await bot.say('Channel "{0}" not found. Please check the spelling.'.format(channelname))
        return

    dbsession = Session()

    channel_db = dbsession.query(WhitelistedChannel).get(channel_obj.id)
    if not channel_db:
        await bot.say('Channel "{0}" is not whitelisted.'.format(channel_obj.name))
        return

    dbsession.delete(channel_db)
    dbsession.commit()
    await bot.say('Removed channel "{0}" from whitelist.'.format(channel_obj.name))