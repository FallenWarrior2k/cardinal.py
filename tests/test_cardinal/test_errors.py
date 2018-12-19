import cardinal.errors as errors


def test_channel_not_whitelisted(mocker):
    ctx = mocker.Mock()
    ctx.channel.mention = '<#123456789>'
    ex = errors.ChannelNotWhitelisted(ctx)
    expected = 'Channel {} is not whitelisted.'.format(ctx.channel.mention)
    got = str(ex)
    assert expected == got
    assert ctx.channel is ex.channel


def test_user_blacklisted(mocker):
    ctx = mocker.Mock()
    ex = errors.UserBlacklisted(ctx)
    assert ctx.author is ex.user
