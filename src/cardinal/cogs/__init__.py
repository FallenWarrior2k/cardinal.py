from logging import getLogger

from dependency_injector.containers import DeclarativeContainer
from dependency_injector.providers import (
    Configuration,
    DependenciesContainer,
    Singleton,
)

from .anilist import Anilist
from .botadmin import BotAdmin
from .channels import Channels
from .jisho import Jisho
from .moderation import Moderation
from .mute import Mute
from .newbie import Newbies
from .notifications import Notifications
from .roles import Roles
from .saucenao import SauceNAO
from .stop import Stop
from .whitelist import Whitelisting

logger = getLogger(__name__)
cog_names = (
    "anilist",
    "botadmin",
    "channels",
    "jisho",
    "moderation",
    "mute",
    "newbie",
    "notifications",
    "roles",
    "saucenao",
    "stop",
    "whitelist",
)


class CogsContainer(DeclarativeContainer):
    root = DependenciesContainer()
    # Accessing a Configuration through a DependenciesContainer does not work, so do it manually
    config = Configuration("config.cogs")

    anilist = Singleton(Anilist, http=root.http)

    botadmin = Singleton(BotAdmin, http=root.http)

    channels = Singleton(Channels)

    jisho = Singleton(Jisho, http=root.http)

    moderation = Singleton(Moderation)

    mute = Singleton(
        Mute,
        bot=root.bot,
        loop=root.loop,
        scoped_session=root.scoped_session,
        sessionmaker=root.sessionmaker,
    )

    newbie = Singleton(
        Newbies,
        bot=root.bot,
        loop=root.loop,
        scoped_session=root.scoped_session,
        sessionmaker=root.sessionmaker,
    )

    notifications = Singleton(Notifications, scoped_session=root.scoped_session)

    roles = Singleton(Roles)

    saucenao = Singleton(SauceNAO, http=root.http, api_key=config.saucenao.api_key)

    stop = Singleton(Stop)

    whitelist = Singleton(Whitelisting)


def load_cogs(root):
    bot = root.bot()
    cogs = CogsContainer(root=root, config=root.config.cogs())

    for cog_name in cog_names:
        cog_provider = getattr(cogs, cog_name)
        bot.add_cog(cog_provider())
