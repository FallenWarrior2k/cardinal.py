from discord.ext import commands
from lazy import lazy

from .errors import IllegalSessionUse


class Context(commands.Context):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.session_allowed = False
        self.session_used = False

    @lazy
    def session(self):
        if not self.session_allowed:
            raise IllegalSessionUse()

        self.session_used = True
        return self.bot.sessionmaker()

