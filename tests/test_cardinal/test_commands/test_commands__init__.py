import logging
import unittest.mock as mock

import discord.ext.commands as _commands
import pytest

from cardinal import commands


def test_cog_ctor():
    bot = mock.Mock()
    cog = commands.Cog(bot)

    assert cog.bot is bot


class TestAllSubclasses:
    @pytest.fixture()
    def cls_mock(self):
        return mock.MagicMock()

    def test_no_subclasses(self, cls_mock):
        cls_mock.__subclasses__ = mock.Mock(return_value=[])

        flatiter = commands.all_subclasses(cls_mock)
        with pytest.raises(StopIteration):
            next(flatiter)

    def test_no_nested_subclasses(self, cls_mock):
        flatlist = []

        for i in range(5):
            cur = mock.MagicMock()
            cur.__subclasses__ = mock.Mock(return_value=[])
            flatlist.append(cur)

        cls_mock.__subclasses__ = mock.Mock(return_value=flatlist)

        flatiter = commands.all_subclasses(cls_mock)

        for expected, got in zip(flatlist, flatiter):
            assert expected is got

    def test_nested_subclasses(self, cls_mock):
        cur, sub = mock.MagicMock(), mock.MagicMock()
        flatlist = [cur]
        cls_mock.__subclasses__ = mock.Mock(return_value=[cur])

        for i in range(5):
            cur.__subclasses__ = mock.Mock(return_value=[sub])
            sub.__subclasses__ = mock.Mock(return_value=[])
            flatlist.append(sub)
            cur, sub = sub, mock.MagicMock()

        flatiter = commands.all_subclasses(cls_mock)

        for expected, got in zip(flatlist, flatiter):
            assert expected is got

    def test_mixed(self, cls_mock):
        cls_list = [mock.MagicMock() for i in range(5)]
        flatlist = cls_list[:]

        for cls in cls_list:
            cur, sub = mock.MagicMock(), mock.MagicMock()
            cls.__subclasses__ = mock.Mock(return_value=[cur])
            flatlist.append(cur)

            for i in range(5):
                cur.__subclasses__ = mock.Mock(return_value=[sub])
                sub.__subclasses__ = mock.Mock(return_value=[])
                flatlist.append(sub)
                cur, sub = sub, mock.MagicMock()

        cls_mock.__subclasses__ = mock.Mock(return_value=cls_list)
        flatiter = commands.all_subclasses(cls_mock)

        for expected, got in zip(flatlist, flatiter):
            assert expected is got


class TestSetup:
    @pytest.fixture()
    def patches(self, mocker):
        iter_modules = mocker.patch('pkgutil.iter_modules')
        import_module = mocker.patch('importlib.import_module')
        all_subclasses = mocker.patch('cardinal.commands.all_subclasses')
        return {
            'iter_modules': iter_modules,
            'import_module': import_module,
            'all_subclasses': all_subclasses
        }

    @pytest.fixture(params=[
        [],
        [(mock.Mock(), 'test_module', False),
         (mock.Mock(), 'other_test_module', True),
         (mock.Mock(), 'another_test_module', False)]
    ])
    def modules(self, request, patches):
        patches['iter_modules'].return_value = request.param
        return request.param

    @pytest.fixture(params=[
        [],
        [mock.MagicMock(__name__='test mock', return_value=mock.Mock())]
    ])
    def subclasses(self, request, patches):
        patches['all_subclasses'].return_value = request.param
        return request.param

    def test_no_exception(self, patches, caplog, modules, subclasses):
        bot = mock.Mock(spec=_commands.Bot)

        with caplog.at_level(logging.INFO, logger=commands.__name__):
            commands.setup(bot)

        patches['iter_modules'].assert_called_once_with(commands.__path__)
        patches['all_subclasses'].assert_called_once_with(commands.Cog)
        for record in caplog.records:
            assert record.levelname != 'ERROR'

        for _, mod_name, is_pkg in modules:
            if not is_pkg:
                patches['import_module'].assert_any_call('.' + mod_name, commands.__name__)

        if all(is_pkg for *_, is_pkg in modules):
            patches['import_module'].assert_not_called()

        if not subclasses:
            bot.add_cog.assert_not_called()

        for cls in subclasses:
            assert (commands.__name__, logging.INFO,
                    'Initializing "{}".'.format(cls.__name__)) in caplog.record_tuples

            cls.assert_called_with(bot)
            bot.add_cog.assert_any_call(cls.return_value)

    def test_import_exception(self, patches, caplog, modules):
        bot = mock.Mock(spec=_commands.Bot)
        patches['import_module'].side_effect = (Exception(), None)

        commands.setup(bot)

        if all(is_pkg for *_, is_pkg in modules):
            patches['import_module'].assert_not_called()
        else:
            assert patches['import_module'].called
            assert 'ERROR' in [record.levelname for record in caplog.records]

        for _, mod_name, is_pkg in modules:
            if not is_pkg:
                patches['import_module'].assert_any_call('.' + mod_name, commands.__name__)

    @pytest.mark.usefixtures('patches')
    def test_init_exception(self, caplog, subclasses):
        bot = mock.Mock(spec=_commands.Bot)

        if subclasses:
            subclasses[0].side_effect = Exception()

        commands.setup(bot)

        if subclasses:
            assert 'ERROR' in [record.levelname for record in caplog.records]

        for cls in subclasses:
            cls.assert_any_call(bot)

            if not cls.side_effect:
                bot.add_cog.assert_any_call(cls.return_value)
