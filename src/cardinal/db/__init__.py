from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from __main__ import config

engine = create_engine(config['db_connectstring'])
Base = declarative_base()
Session = sessionmaker()
Session.configure(bind=engine)