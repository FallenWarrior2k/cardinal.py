from aiohttp import ClientSession
from discord import Activity, ActivityType
from discord.ext.commands import Cog, bot_has_permissions, command, is_owner

from ..utils import maybe_send


class BotAdmin(Cog):
    """
    Bot administration commands for the owner.
    """

    def __init__(self, http: ClientSession):
        self._http = http

    @command(aliases=["makeinvite", "getinvite", "invitelink"])
    @is_owner()
    async def invite(self, ctx):
        """
        Generate an invite link to add the bot to other servers.

        Required permissions:
            - Bot owner
        """
        await ctx.send(
            "Invite link for {0.mention}: "
            "<https://discordapp.com/oauth2/authorize?client_id={0.id}&scope=bot>".format(
                ctx.me
            )
        )

    @command()
    @is_owner()
    @bot_has_permissions(manage_messages=True)
    async def say(self, ctx, *, msg: str):
        """
        Send a message that looks like it came from the bot itself.

        Required permissions:
            - Bot owner

        Required bot permissions:
            - Manage Messages

        Parameters:
            - msg: Text the bot should send.
        """
        await ctx.message.delete()
        await maybe_send(ctx, msg)

    @command(aliases=["setpfp"])
    @is_owner()
    async def setavatar(self, ctx, url: str = None):
        """
        Change the bot's avatar. Takes a URL or an attachment.

        Required permissions:
            - Bot owner

        Parameters:
            - [optional] url: Image to set the avatar to.
            Omission unsets avatar if no attachment is present.
        """
        if not url and ctx.message.attachments:
            url = ctx.message.attachments[0].url

        if url:
            async with self._http.get(url) as resp:
                if not resp.content_type.startswith("image/"):
                    await maybe_send(ctx, "The given file or URL is not an image.")
                    return

                data = await resp.read()
        else:
            data = None

        await ctx.bot.user.edit(avatar=data)

    @command()
    @is_owner()
    async def setstatus(self, ctx, prefix: str, *, text: str):
        """
        Set the status displayed on the bot's profile.

        Required permissions:
            - Bot owner

        Parameters:
            - prefix: What type of status to set,
            i.e. "playing", "streaming", "listening", or "watching".
            - text: Status text to display after the type.
        """
        try:
            activity_type = ActivityType[prefix.lower()]
        except KeyError:
            await maybe_send(ctx, f'"{prefix}" is not a valid type of status.')
            return

        activity = Activity(type=activity_type, name=text)
        await ctx.bot.change_presence(activity=activity)

    @command(aliases=["kill"])
    @is_owner()
    async def shutdown(self, ctx):
        """
        Shut the bot down entirely.

        Required permissions:
            - Bot owner
        """
        await maybe_send(ctx, "Shutting down.")
        await ctx.bot.close()
