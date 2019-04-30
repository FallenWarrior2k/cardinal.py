from discord.ext.commands import Cog


class BaseCog(Cog):
    def __init__(self, bot):
        self.bot = bot
