import discord.ext.commands as commands


class Context(commands.Context):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.session_scope = self.bot.session_scope
