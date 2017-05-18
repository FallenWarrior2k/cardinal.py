from discord.ext.commands import check
from cardinal import Session
from cardinal.models import WhitelistedChannel


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