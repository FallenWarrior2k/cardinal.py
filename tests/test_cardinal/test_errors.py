from cardinal.errors import ChannelNotWhitelisted, UserBlacklisted


def test_channel_not_whitelisted(mocker):
    ctx = mocker.Mock()
    ctx.channel.mention = "<#123456789>"
    ex = ChannelNotWhitelisted(ctx)
    expected = f"Channel {ctx.channel.mention} is not whitelisted."
    got = str(ex)
    assert expected == got
    assert ctx.channel is ex.channel


def test_user_blacklisted(mocker):
    ctx = mocker.Mock()
    ex = UserBlacklisted(ctx)
    assert ctx.author is ex.user
