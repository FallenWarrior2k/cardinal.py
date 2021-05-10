from pytest import fixture

from cardinal.cogs import cog_names, load_cogs


@fixture
def container(mocker):
    return mocker.patch("cardinal.cogs.CogsContainer")


def test_load_cogs(container, mocker):
    root = mocker.Mock()
    load_cogs(root)

    root.bot.assert_called_with()  # Singleton, doesn't matter how often it was called
    container.assert_called_once_with(root=root, config=root.config.cogs())

    for cog_name in cog_names:
        cog_provider = getattr(container.return_value, cog_name)
        cog_provider.assert_called_once_with()
        root.bot.return_value.add_cog.assert_any_call(cog_provider.return_value)
