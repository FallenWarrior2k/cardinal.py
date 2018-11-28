import unittest.mock as mock
from itertools import islice

import pytest
from discord.ext import commands

from cardinal import cogs


class TestSetup:
    @pytest.fixture
    def bot(self, mocker):
        return mocker.Mock(spec=commands.Bot)

    @pytest.fixture
    def cog_list(self, request, mocker):
        mocker.patch('cardinal.cogs.cogs', new=request.param)
        return request.param

    @pytest.mark.parametrize(
        ['cog_list'],
        [
            ([],),
            ([mock.MagicMock(__name__='test mock 1')],),
            ([
                 mock.MagicMock(__name__='test mock 2'),
                 mock.MagicMock(__name__='test mock 3'),
                 mock.MagicMock(__name__='test mock 4')
             ],)
        ],
        indirect=['cog_list']
    )
    def test_no_exception(self, bot, cog_list):
        cogs.setup(bot)

        for i, cog in enumerate(cog_list):
            cog.assert_called_once_with(bot)
            assert ((cog.return_value,), {}) == bot.add_cog.call_args_list[i]

    @pytest.mark.parametrize(
        ['cog_list'],
        [
            ([mock.MagicMock(__name__='test mock 1', side_effect=Exception('mock exception 1'))],),
            ([
                 mock.MagicMock(__name__='test mock 2'),
                 mock.MagicMock(__name__='test mock 3', side_effect=Exception('mock exception 2')),
                 mock.MagicMock(__name__='test mock 4')
             ],)
        ],
        indirect=['cog_list']
    )
    def test_exception(self, bot, cog_list):
        # Retrieve the first exception that will be raised, which should also be re-raised
        first_exc_cog, first_exc_i = next((_c, i) for i, _c in enumerate(cog_list)
                                            if _c.side_effect)

        with pytest.raises(Exception, message=str(first_exc_cog.side_effect)):
            cogs.setup(bot)

        # Check cogs that came before the one with the exception
        for i, cog in enumerate(islice(cog_list, first_exc_i)):
            cog.assert_called_once_with(bot)
            assert ((cog.return_value,), {}) == bot.add_cog.call_args_list[i]

        first_exc_cog.assert_called_once_with(bot)
        assert ((first_exc_cog.return_value,), {}) not in bot.add_cog.call_args_list

        for cog in islice(cog_list, first_exc_i + 1, None):
            cog.assert_not_called()
            assert ((cog.return_value,), {}) not in bot.add_cog.call_args_list
