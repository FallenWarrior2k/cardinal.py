from discord.ext.commands import Context as BaseContext


class Context(BaseContext):
    def __init__(self, scoped_session, **kwargs):
        super().__init__(**kwargs)
        self.session = scoped_session  # TODO: Ensure everything actually commits its changes
