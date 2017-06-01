def clean_prefix(ctx):
    user = ctx.bot.user
    return ctx.prefix.replace(user.mention, '@' + user.name)