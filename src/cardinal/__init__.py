import logging
import sys
from discord.ext import commands
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from cardinal.config import load_config

logging.basicConfig(level=logging.WARNING)

if not len(sys.argv) > 1:
    print('Please pass the path of the config file as the first command-line argument')
    sys.exit(1)

config = load_config(sys.argv[1])

bot = commands.Bot(command_prefix=config['cmd_prefix'], description='cardinal.py')

engine = create_engine(config['db_connectstring'])
Base = declarative_base()
Session = sessionmaker()
Session.configure(bind=engine)


@bot.event
async def on_ready():
    print('Logged into Discord as')
    try:
        print('%s#%s' % (bot.user.name, bot.user.discriminator))
    except:
        pass

    print('\n')

from cardinal.commands import channels

bot.run(config['token'])