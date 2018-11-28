from discord.ext import commands


class ChannelNotWhitelisted(commands.CheckFailure):
    def __init__(self, ctx: commands.Context):
        self.channel = ctx.channel
        m = 'Channel {} is not whitelisted.'.format(ctx.channel.mention)
        super().__init__(m)


class UserBlacklisted(commands.CheckFailure):
    def __init__(self, ctx: commands.Context):
        self.user = ctx.author


class PromptTimeout(Exception):
    pass
