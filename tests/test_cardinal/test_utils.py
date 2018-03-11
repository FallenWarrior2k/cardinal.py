import unittest as ut
import unittest.mock as mock

import cardinal.utils as utils


class FormatNamedEntityTestCase(ut.TestCase):
    def test__format_named_entity(self):
        obj = mock.NonCallableMock()
        obj.name = 'Test obj'
        obj.id = 123456789

        expected = '"{0.name}" ({0.id})'.format(obj)
        got = utils._format_named_entity(obj)

        self.assertMultiLineEqual(expected, got)


@mock.patch('cardinal.utils._format_named_entity')
class FormatNamedEntitiesTestCase(ut.TestCase):
    def setUp(self):
        good_arg = mock.NonCallableMock()
        good_arg.name = 'Test object'
        good_arg.id = 123456789
        self.good_arg = good_arg

        bad_arg = mock.NonCallableMock(spec=object)
        self.bad_arg = bad_arg

        good_args = (good_arg, good_arg)
        self.good_args = good_args

        bad_args = (bad_arg, bad_arg)
        self.bad_args = bad_args

        mixed_args = (good_arg, bad_arg)
        self.mixed_args = mixed_args

    def test_empty_args(self, _format_named_entity):
        _iter = utils.format_named_entities()

        with self.assertRaises(StopIteration):
            next(_iter)

        _format_named_entity.assert_not_called()

    def test_one_correct_arg(self, _format_named_entity):
        _iter = utils.format_named_entities(self.good_arg)
        self.assertIs(next(_iter), _format_named_entity.return_value)
        _format_named_entity.assert_called_once_with(self.good_arg)

        with self.assertRaises(StopIteration):
            next(_iter)

    def test_one_bad_arg(self, _format_named_entity):
        _iter = utils.format_named_entities(self.bad_arg)

        with self.assertRaises(StopIteration):
            next(_iter)

        _format_named_entity.assert_not_called()

    def test_two_good_args(self, _format_named_entity):
        _iter = utils.format_named_entities(*self.good_args)

        self.assertIs(next(_iter), _format_named_entity.return_value)
        self.assertIs(next(_iter), _format_named_entity.return_value)

        call = mock.call(self.good_arg)
        _format_named_entity.assert_has_calls([call, call])

        with self.assertRaises(StopIteration):
            next(_iter)

    def test_two_bad_args(self, _format_named_entity):
        _iter = utils.format_named_entities(*self.bad_args)

        with self.assertRaises(StopIteration):
            next(_iter)

        _format_named_entity.assert_not_called()

    def test_one_good_arg_one_bad_arg(self, _format_named_entity):
        _iter = utils.format_named_entities(*self.mixed_args)

        self.assertIs(next(_iter), _format_named_entity.return_value)
        _format_named_entity.assert_called_once_with(self.good_arg)

        with self.assertRaises(StopIteration):
            next(_iter)

        _format_named_entity.assert_called_once_with(self.good_arg)


class FormatMessageTestCase(ut.TestCase):
    def setUp(self):
        msg = mock.NonCallableMock()
        msg.content = 'Test message'
        msg.author.name = 'Test author name'
        msg.author.id = 123456789
        msg.guild = None
        self.msg = msg

    def test_dm(self):
        expected = '[DM] {0.author.name} ({0.author.id}): {0.content}'.format(self.msg)
        got = utils.format_message(self.msg)
        self.assertMultiLineEqual(expected, got)

    def test_guild(self):
        self.msg.guild = mock.NonCallableMock()
        self.msg.guild.name = 'Test guild'
        self.msg.guild.id = 987654321
        self.msg.channel.name = 'Test channel'
        self.msg.channel.id = 123459876

        expected = '[{0.guild.name} ({0.guild.id}) -> #{0.channel.name} ({0.channel.id})] {0.author.name} ({0.author.id}): {0.content}'.format(self.msg)
        got = utils.format_message(self.msg)
        self.assertMultiLineEqual(expected, got)


class CleanPrefixTestCase(ut.TestCase):
    def setUp(self):
        ctx = mock.NonCallableMock()
        ctx.me.mention = '<@123456789>'
        ctx.me.name = 'Test bot'
        ctx.guild = None
        self.ctx = ctx

    def test_regular_dm(self):
        self.ctx.prefix = '?'
        expected = '?'
        got = utils.clean_prefix(self.ctx)
        self.assertMultiLineEqual(expected, got)

    def test_mention_dm(self):
        self.ctx.prefix = self.ctx.me.mention
        expected = '@{}'.format(self.ctx.me.name)
        got = utils.clean_prefix(self.ctx)
        self.assertMultiLineEqual(expected, got)

    def test_regular_guild_no_nick(self):
        self.ctx.guild = True
        self.ctx.me.nick = None
        self.ctx.prefix = '?'
        expected = '?'
        got = utils.clean_prefix(self.ctx)
        self.assertMultiLineEqual(expected, got)

    def test_mention_guild_no_nick(self):
        self.ctx.guild = True
        self.ctx.me.nick = None
        self.ctx.prefix = self.ctx.me.mention
        expected = '@{}'.format(self.ctx.me.name)
        got = utils.clean_prefix(self.ctx)
        self.assertMultiLineEqual(expected, got)

    def test_regular_guild_nick(self):
        self.ctx.guild = True
        self.ctx.me.nick = 'Test nick'
        self.ctx.prefix = '?'
        expected = '?'
        got = utils.clean_prefix(self.ctx)
        self.assertMultiLineEqual(expected, got)

    def test_mention_guild_nick(self):
        self.ctx.guild = True
        self.ctx.me.nick = 'Test nick'
        self.ctx.prefix = self.ctx.me.mention
        expected = '@{}'.format(self.ctx.me.nick)
        got = utils.clean_prefix(self.ctx)
        self.assertMultiLineEqual(expected, got)
