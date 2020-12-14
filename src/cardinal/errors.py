from discord.ext.commands import CheckFailure


class ChannelNotWhitelisted(CheckFailure):
    def __init__(self, ctx):
        self.channel = ctx.channel
        m = f'Channel {ctx.channel.mention} is not whitelisted.'
        super().__init__(m)


class UserBlacklisted(CheckFailure):
    def __init__(self, ctx):
        self.user = ctx.author


class PromptTimeout(Exception):
    pass


class IllegalSessionUse(Exception):
    pass
