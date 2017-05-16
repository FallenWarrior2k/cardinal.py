import discord.utils
from discord.ext.commands import check
from cardinal import Session
from cardinal.models import WhitelistedChannel


def get_channel_by_name(ctx, channel: str):
    channel = channel.lstrip('#')
    guild = ctx.message.server

    if guild is None:
        return None

    return discord.utils.get(guild.channels, name=channel)


def channel_whitelisted():
    def predicate(ctx):
        channel_obj = ctx.message.channel

        dbsession = Session()
        channel_db = dbsession.query(WhitelistedChannel).get(channel_obj.id)

        if channel_db:
            return True
        else:
            return False

    return check(predicate)