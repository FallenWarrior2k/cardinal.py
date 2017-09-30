import logging

from sqlalchemy.ext.declarative import declarative_base

logger = logging.getLogger(__name__)
Base = declarative_base()


def create_all(engine):
    Base.metadata.create_all(engine)
    logger.info('Created necessary database tables.')
