from asyncio import get_event_loop
from logging import getLogger

from aiohttp import ClientSession
from dependency_injector.containers import DeclarativeContainer
from dependency_injector.providers import (
    Callable,
    Configuration,
    DelegatedFactory,
    Factory,
    Singleton,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session as _scoped_session
from sqlalchemy.orm import sessionmaker as _sessionmaker

from .bot import Bot, event_context
from .context import Context

logger = getLogger(__name__)


def _create_engine_wrapper(connect_string, options):
    return create_engine(connect_string, **options)


class RootContainer(DeclarativeContainer):
    """Application IoC container"""

    config = Configuration("config")
    loop = Singleton(get_event_loop)

    # Remote services
    engine = Singleton(
        _create_engine_wrapper, config.db.connect_string, config.db.options
    )

    http = Factory(ClientSession, loop=loop, raise_for_status=True)

    sessionmaker = Singleton(_sessionmaker, bind=engine)

    scoped_session = Singleton(
        _scoped_session, sessionmaker, scopefunc=event_context.get
    )

    context_factory = DelegatedFactory(Context, scoped_session=scoped_session)

    bot = Singleton(
        Bot,
        command_prefix=config.cmd_prefix,
        context_factory=context_factory,
        default_game=config.default_game,
        loop=loop,
        scoped_session=scoped_session,
    )

    # Main
    run_bot = Callable(Bot.run, bot, config.token)
