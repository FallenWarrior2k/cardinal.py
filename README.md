# cardinal.py
[![Build Status](https://travis-ci.org/FallenWarrior2k/cardinal.py.svg?branch=master)](https://travis-ci.org/FallenWarrior2k/cardinal.py)
[![Coverage Status](https://coveralls.io/repos/github/FallenWarrior2k/cardinal.py/badge.svg?branch=master)](https://coveralls.io/github/FallenWarrior2k/cardinal.py?branch=master)
[![Requirements Status](https://requires.io/github/FallenWarrior2k/cardinal.py/requirements.svg?branch=master)](https://requires.io/github/FallenWarrior2k/cardinal.py/requirements/?branch=master)

A growing, general-purpose, all-round Discord bot.

## Features

### Management and server structure
* Join/leave/ban/unban notifications
* Selfroling
* Opt-in channels, i.e. hidden channels that only appear to users after issuing a command
* Restricting bot commands to certain channels (due to be replaced/reworked in a future version)
* Restricting new members' privileges until they confirm themselves (due for removal because of the Welcome Screen feature for community servers)

### Moderation
* Kicking and banning
* Muting (restricts Send Messages and Add Reactions in all channels)
* Stopping: restricts message sending in channel until a corresponding `stop off` command is issued

### Owner commands
* Generate an invite link for the bot
* Make the bot say things
* Set the bot's avatar to an image supplied by URL or attachment
* Set the bot's playing/streaming/listening status
* Shut the bot down

### Utility
* [AniList](https://anilist.co) lookup of anime, manga, and light novels
* Lookup of terms in [Jisho](https://jisho.org), a Japanese-English dictionary
* Lookup of images in the [SauceNAO](https://saucenao.com) reverse image search database

Albeit quite short right now, this list will probably grow in due time.

## Prerequisites
In any case, you will need a Discord Bot Token. It can be retrieved from the "Bot" tab after creating or selecting an application [here](https://discordapp.com/developers/applications/me).
If no bot user exists, you will need to click the "Add Bot" button first.
Once you have a bot, you can get the token by clicking "Click to Reveal Token".
This is confidential and should never be shared.

### Manual setup
If you choose not to use the Docker image, this is what you need to set up the bot manually.

* a [Python](https://www.python.org/downloads/) version supported by the bot, currently 3.8+
* pip3; on Windows, it is included in Python, on Linux it can _usually_ be acquired from the package `python3-pip`

### Docker
The [Docker images](https://hub.docker.com/r/fallenwarrior2k/cardinal.py) take care of a lot of the setup work required.
They currently require the config file to be mounted at `/cardinal/config.json`,
but future plans include adding an environment variable to allow for customisation of that path.

As for databases, the probably easiest solution is to put a container running your preferred DBMS on a network connected to the bot container
and use that in the `"connect_string"` config key.

However, public images currently only specify dependencies for `psycopg2`, the default database driver for PostgreSQL.
To use the bot with a different database, adjust the dependency files in `docker/` and build the image yourself.

* `apk-build.txt`: Build-time dependencies that are removed after the image is built
* `apk-rt.txt`: Runtime dependencies that are not removed after build
* `requirements.txt`: pip dependencies, should contain the driver you want to use

As with the config location, I plan for some way to adjust these dependencies more easily, although at a much lower priority.

### Database
Due to SQLite not working well with Alembic, it is advised to use an actual database server.
I personally use the [PostgreSQL](https://www.postgresql.org/) [Docker image](https://hub.docker.com/_/postgres/),
so while I try not to depend on its specifics, other DBMSs might not work properly.

MySQL is explicitly not supported, as the database code makes use of `CHECK` constraints, which are not supported by any of MySQL's engines.

`SAVEPOINTS` should also be supported, as SQLAlchemy's [`Session.begin_nested()`](https://docs.sqlalchemy.org/en/latest/orm/session_api.html#sqlalchemy.orm.session.Session.begin_nested)
depends on them being available.

If you decide to choose PostgreSQL as your database backend,
you will also need the `postgresql-dev` and `libpq` packages from your package manager,
as well as `psycopg2` from pip.
`postgresql-dev` is a build-time dependency and can be removed after `psycopg2` is done installing.

## Setup

The following commands assume that you have a valid Python 3 interpreter and pip3 on your path as `python` and `pip`, respectively.
This is usually not the global default on Linux systems, as those spots tend to be taken by the Python 2 counterparts.

However, if you intend to use Python for anything other than this bot,
you should consider using an isolated environment via [virtualenv](https://virtualenv.pypa.io/) or [venv](https://docs.python.org/3/library/venv.html)
anyways, and those have `python` and `pip` referring to the Python 3 versions.

Firstly, open a terminal and navigate to the bot's directory.

    cd /path/to/download/cardinal.py

Install the necessary dependencies. This might need `sudo` if you are using global pip.

    pip install .

Now fill out the config file (located at `config.json.example` in the repository's root directory) and rename it to `config.json`.

* `"token"`: Bot token to use. Copy over the one you obtained in the prerequisites.
* `"cmd_prefix"`: Command prefix to use for the bot.
    This can be anything, but it's usually a single character.
    It also should not overlap with existing bots in the servers you intend to use this bot.
* `"default_game`: What should be displayed as the bot's "Playing ...". Might add a command in future to make it dynamic.
* `"db"`: A multitude of options on how to access the database, most importantly instructions on how to connect.
    - `"connect_string`: Database URL in conformance with SQLAlchemy's [limitations](https://docs.sqlalchemy.org/en/latest/core/engines.html#database-urls).
        Note that installing the respective drivers and their dependencies is up to the user;
        the bot does not include any specific drivers in its dependencies.
    - `"options"`: Custom requirements on how to create the database engine used by the bot.
        Essentially passed through to [`create_engine`](https://docs.sqlalchemy.org/en/latest/core/engines.html#sqlalchemy.create_engine) as `**kwargs`.
* `"log_level"`: Log level of the bot. Essentially dictates how "major" an event must be to get logged.
    The default level is `INFO`, which logs some informative messages like command invocations in addition to just errors.
    Other options are `WARNING`, `ERROR` and `FATAL`, which do what they say, as well as `DEBUG` which prints just about everything.
* `"cogs"`: This is where cog-specific settings live.
    Cogs are the modules/units of related code that provide most functionality, primarily commands.
    - `"saucenao"`: Settings for the SauceNAO cog; permits customizing the way in which it interacts with the API.
        + `"api_key"`: SauceNAO API key (see [here](https://saucenao.com/user.php?page=search-api)) used to authenticate requests against the API.
        Can be empty, garbage, or not even present if you don't want to use the SauceNAO functionality,
        but this will cause all related commands to error out.

After filling out the configuration, you will need to run the `upgrade_db.py` script,
which creates the database tables needed for operation.
This command needs to be re-run when the bot is updated to ensure the database structure is up-to-date.

    python upgrade_db.py

Finally, after ensuring the correctness of the database structure, you will need to start the bot.

    python run_cardinal.py

## Roadmap

### Features
* Replicate the actively used features of [Shinoa](https://github.com/Dormanil/Shinoa)
* Anilist "Next episode lookups" (idea taken from [Euphemia](https://github.com/jokersus/Euphemia)'s `;next`)
* Custom CLI to replace and extend `upgrade_db.py` and `run_cardinal.py`
* Generalised RSS tracking
* Embeds or otherwise customised responses
* Per-server prefixes to prevent prefix clashes/overlaps with other bots
* Group pings that are not role-based (idea taken from [Euphemia](https://github.com/jokersus/Euphemia)'s `;tag`)
* Management commands for bot owner
* Custom responses for certain triggers
* "Bound" commands, i.e. creating a new command that locks arguments for another command to certain values;
    to be used as shortcuts for often used commands

### Internals
* [Tox](https://tox.readthedocs.io/en/latest/) coverage tracking
* Tox-based [Travis](https://travis-ci.com) build matrix
* Tests for the commands, as well as any future additions

## Built with
* [discord.py](https://github.com/Rapptz/discord.py) as the Discord API wrapper
* [SQLAlchemy](https://www.sqlalchemy.org/) and [Alembic](https://alembic.sqlalchemy.org/en/latest/) for database handling and management
* [dependency_injector](http://python-dependency-injector.ets-labs.org/) for dependency injection and IoC
* [aioitertools](https://github.com/omnilib/aioitertools) to make dealing with async iterators and generators more convenient
* [markdownify](https://github.com/matthewwithanm/python-markdownify) to convert HTML to Markdown so that Discord can understand it

## Acknowledgments
* [@Dormanil](https://github.com/Dormanil) and [@OmegaVesko](https://github.com/OmegaVesko)
    for the [Shinoa](https://github.com/Dormanil/Shinoa) project we worked on together,
    as it was a major inspiration for this bot and a whole lot of functionality is or will be taken directly from it.

* [@jokersus](https://github.com/jokersus) because the code backing the Anilist commands was inspired by
    and loosely based on the code for a similar functionality in his [Euphemia](https://github.com/jokersus/Euphemia) project.
