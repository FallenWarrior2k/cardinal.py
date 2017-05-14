import discord.utils

def get_channel(ctx, channel: str):
    channel = channel.lstrip('#')
    guild = ctx.message.server

    if guild is None:
        return None

    return discord.utils.get(guild.channels, name=channel)
