from cardinal.cogs.basecog import BaseCog


def test_basecog_ctor(mocker):
    bot = mocker.Mock()
    cog = BaseCog(bot)

    assert cog.bot is bot
