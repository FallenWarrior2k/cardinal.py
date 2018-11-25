import unittest.mock as mock

import pytest
from discord.ext import commands

from cardinal import cogs


@pytest.fixture
def bot(mocker):
    return mocker.Mock(spec=commands.Bot)


@pytest.fixture
def cog_list(request, mocker):
    mocker.patch('cardinal.cogs.cogs', new=request.param)
    return request.param


@pytest.mark.parametrize(
    ['cog_list'],
    [
        ([],),
        ([mock.MagicMock(__name__='test mock 1')],),
        ([mock.MagicMock(__name__='test mock 2', side_effect=Exception())],),
        ([
             mock.MagicMock(__name__='test mock 3'),
             mock.MagicMock(__name__='test mock 4', side_effect=Exception()),
             mock.MagicMock(__name__='test mock 5')
         ],)
    ],
    indirect=['cog_list']
)
def test_setup(bot, cog_list):
    cogs.setup(bot)

    i = 0  # Index for call args list
    for cog in cog_list:
        cog.assert_called_once_with(bot)

        if cog.side_effect and i < len(bot.add_cog.call_args_list):
            assert ((cog.return_value,), {}) != bot.add_cog.call_args_list[i]
        elif not cog.side_effect:
            assert i < len(bot.add_cog.call_args_list)
            assert ((cog.return_value,), {}) == bot.add_cog.call_args_list[i]
            i += 1  # Only increment if mock was called
