import discord
from discord.ext import commands

from cardinal import bot
from cardinal.db import Session
from cardinal.db.whitelist import WhitelistedChannel
from cardinal.utils import clean_prefix


@bot.group(pass_context=True, no_pm=True)
@commands.has_permissions(manage_channels=True)
async def whitelist(ctx):
    """Provides functionality for whitelisting channels to allow usage of channel-restricted commands."""
    if ctx.invoked_subcommand is None:
        await bot.say('Invalid command passed. Possible choices are "add" and "remove".\nPlease refer to `{prefix}help {command}` for further information.'.format(prefix=clean_prefix(ctx), command=ctx.invoked_with))
        return

@whitelist.command(pass_context=True)
async def add(ctx, channel: discord.Channel = None):
    """Adds a channel to the whitelist."""
    if channel is None:
        channel = ctx.message.channel

    dbsession = Session()

    if dbsession.query(WhitelistedChannel).get(channel.id):
        await bot.say('Channel {0} is already whitelisted.'.format(channel.mention))
        return

    channel_db = WhitelistedChannel(channelid=channel.id)
    dbsession.add(channel_db)
    dbsession.commit()
    await bot.say('Whitelisted channel {0}.'.format(channel.mention))

@whitelist.command(pass_context=True)
async def remove(ctx, channel: discord.Channel = None):
    """Removes a channel from the whitelist."""
    if channel is None:
        channel = ctx.message.channel

    dbsession = Session()

    channel_db = dbsession.query(WhitelistedChannel).get(channel.id)
    if not channel_db:
        await bot.say('Channel {0} is not whitelisted.'.format(channel.mention))
        return

    dbsession.delete(channel_db)
    dbsession.commit()
    await bot.say('Removed channel {0} from whitelist.'.format(channel.mention))