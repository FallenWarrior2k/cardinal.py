import contextlib

import discord.ext.commands as commands


class Context(commands.Context):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @contextlib.contextmanager
    def session_scope(self):
        session = self.bot.sessionmaker()

        try:
            yield session
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()
