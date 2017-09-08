import logging

import discord
import discord.ext.commands as commands

from cardinal.commands import Cog

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class Moderation(Cog):
    def __init__(self, bot):
        super().__init__(bot)

    @commands.command(pass_context=True, no_pm=True)
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    async def kick(self, ctx: commands.Context, user: discord.Member, *, reason: str = None):
        """
        Kick a member from the current server.

        Parameters:
            - user: The member to kick, identified by mention, ID, or name. Must be a member of the server.
            - [optional] reason: The reason for kicking the user. Defaults to empty.

        Required context: Server

        Required permissions:
            - Kick Members

        Required bot permissions:
            - Kick Members
        """

        # TODO: Switch to rewrite for API changes
        await self.bot.kick(user)
        await self.bot.say('User **{}** was kicked by {}.'.format(user.name, ctx.message.author.mention))

    @commands.command(pass_context=True, no_pm=True)
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def ban(self, ctx: commands.Context, user: discord.Member, prune_days: int = 1, *, reason: str = None):
        """
        Ban a user from the current server

        Parameters:
            - user: The member to ban, identified by mention, ID, or name.
            - [optional] prune_days: The amount of days for which the user's message should be pruned. Defaults to one day.
            - [optional] reason: The reason for banning the user. Defaults to empty.

        Required context: Server

        Required permissions:
            - Ban Members

        Required bot permissions:
            - Ban Members
        """

        if prune_days < 0:
            prune_days = 0
        elif prune_days > 7:
            prune_days = 7

        await self.bot.ban(user, prune_days)
        await self.bot.say('User **{}** was banned by {}.'.format(user.name, ctx.message.author.mention))
