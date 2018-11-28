from cardinal import cogs


def test_basecog_ctor(mocker):
    bot = mocker.Mock()
    cog = cogs.BaseCog(bot)

    assert cog.bot is bot
