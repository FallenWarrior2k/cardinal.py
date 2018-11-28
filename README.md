# cardinal.py

[![Build Status](https://travis-ci.org/FallenWarrior2k/cardinal.py.svg?branch=master)](https://travis-ci.org/FallenWarrior2k/cardinal.py)
[![Coverage Status](https://coveralls.io/repos/github/FallenWarrior2k/cardinal.py/badge.svg?branch=master)](https://coveralls.io/github/FallenWarrior2k/cardinal.py?branch=master)
[![Requirements Status](https://requires.io/github/FallenWarrior2k/cardinal.py/requirements.svg?branch=master)](https://requires.io/github/FallenWarrior2k/cardinal.py/requirements/?branch=master)

A growing Discord bot for managing a server.

## Features

- a selfroling system
- opt-in channels, i.e. hidden channels that only appear to users after issuing a command
- restricting bot commands to certain channels
- moderation features like kicking and banning
- restricting new members' privileges until they confirm themselves
- much more to come

## Setup

This is a bit of effort on the user's part, a runscript to automate this will come soon

1. Make sure you have [Python](https://www.python.org/downloads/) 3.5 or above, as well as pip3, installed and on your PATH (this is an option you have to tick while installing). 
On Windows, it comes bundled with Python; on Linux, it can be acquired by downloading the package `python3-pip`
2. Open a terminal in the bot's directory, by shift-clicking the background and selecting "Open command window here" or similar
3. Acquire the necessary package dependencies by executing `pip3 install -r requirements.txt`.
Note that this might require root permissions on Linux systems, unless you are using a [virtualenv](https://virtualenv.pypa.io/).
4. Fill out the config file (located at `config.json.example` in the repository's root directory) and rename it to `config.json`.  

    1. Create a new application under https://discordapp.com/developers/applications/me and convert it into a bot user, using the button displayed after creation
    2. Place the token, revealed by clicking `click to reveal` after the token field on the previous page, into the config file
    3. If desired, customize the command prefix and default status (`default_game`) by changing the respective values.
    4. Should you not be familiar with [SQLAlchemy](https://www.sqlalchemy.org/) or databases in general,
    it is advised to not modify the `db` section of the config file.
    For those who want to make changes, `connect_string` is the first positional parameter passed to 
    [`create_engine`](http://docs.sqlalchemy.org/en/latest/core/engines.html?highlight=create_engine#sqlalchemy.create_engine),
    while `options` is a (possibly empty, but necessary) JSON object, which will be passed as `**kwargs`.
    5. It is possible to change the log level of the bot with the `logging_level` option. The default is `INFO`,
    which logs some informative messages like command invocations in addition to just errors.
    Other options are `WARNING`, `ERROR` and `FATAL`, which do what they say, as well as `DEBUG` which prints everything.
  
5. Run the bot with the command `python3 src` (Linux) or `python src` (Windows).
