import contextlib
import copy
import logging
from yarl import URL
from typing import Optional

import psycopg as pg
from envex import Env

__all__ = (
    "pg_db_info",
    "pg_connect",
    "pg_database_exists",
    "pg_drop_database",
    "pg_setup",
    "pg_dsn",
    "pg_clear_connections",
    "set_env_prefix",
    "set_verbosity",
)


DATABASE_URL = "DATABASE_URL"
SA_DATABASE_URL = "SA_DATABASE_URL"


class EnvironmentNotConfigured(Exception):
    pass



def set_verbosity(verbosity: int = 0):
    verbose = logging.WARN if not verbosity else logging.INFO if verbosity == 1 else logging.DEBUG
    logging.getLogger().setLevel(verbose)


env = Env(readenv=True, exception=EnvironmentNotConfigured)
env_prefix = None

def set_env_prefix(prefix: Optional[str]):
    global env_prefix
    if prefix:
        env_prefix = prefix.upper() if prefix != "-" else None
    elif env.is_set("DJANGO_SITE"):
        env_prefix = env("DJANGO_SITE").upper()
    else:
        env_prefix = env("ENVPREFIX")
    if env_prefix:
        logging.debug(f"Using env_prefix '{env_prefix}'")


def getenv(key: str, default=None):
    if env_prefix:
        # don't use default here, as None is required if the key is not present
        if (value := env(f"{env_prefix}_{key}")) is not None:
            return value
    return env(key, default=default)


class DBUrl:
    __default_pgport = 5432
    __defaults = {
        "scheme": "postgresql",
        "host": getenv("DBHOST"),
        "port": getenv("DBPORT"),
        "name": getenv("DBNAME"),
        "user": getenv("DBUSER"),
        "role": getenv("DBROLE", default=getenv("DBUSER")),
        "password": getenv("DBPASS"),
    }

    def __init__(self, **kwargs):
        """
        Initialize a new instance of the DBUrl class from an optional url.
        Values are sourced from the environment, if available, and can be
        overridden by passing them as keyword arguments.

        Parameters:
        host (str, optional): The host of the database.
        port (str, optional): The port of the database.
        name (str, optional): The name of the database.
        role (str, optional): The role for the database.
        user (str, optional): The user for the database.
        password (str, optional): The password for the database.
        url (str, optional): The url of the database.
        """
        # set values from defaults
        for attr, value in self.__defaults.items():
            setattr(self, attr, value)

        if self.host and ":" in self.host and not self.port:
            self.host, self.port = self.host.split(":", maxsplit=1)

        self.__parse_url(kwargs.get("url", None))

        # allow overrides
        for attr in self.__defaults.keys():
            if (value := kwargs.get(attr, None)) is not None:
                setattr(self, attr, value)

    def __parse_url(self, url):
        """
        Parse the url and set the appropriate values for the instance.
        :param url: str|None url to parse, otherwise sourced from the environment
        """
        if not url:
            url = getenv("DATABASE_URL") or getenv("DJANGO_DATABASE_URL")
        if url and (parsed_url := URL(url)):
            self.scheme = parsed_url.scheme.replace("postgresql+psycopg2", "postgresql")
            self.host = parsed_url.host
            self.port = parsed_url.port
            self.name = parsed_url.path.lstrip("/")
            self.user = self.role = parsed_url.user
            self.password = parsed_url.password

    def to_dict(self):
        return dict(
            scheme=self.scheme,
            host=self.host,
            port=self.port,
            name=self.name,
            user=self.user,
            role=self.role,
            pswd=self.password,
        )

    def copy(self, **kwargs):
        copied = copy.copy(self)
        for attr, value in kwargs.items():
            setattr(copied, attr, value)
        return copied

    def url(self):
        return (
            f"{self.scheme}://{self.user}:{self.password}@{self.host}:{self.port or self.__default_pgport}/{self.name}"
        )

    def log_url(self) -> str:
        return self.copy(password="****").url()

    def __getitem__(self, key):
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(key)

    def __repr__(self):
        return f"{self.__class__.__name__} {self.to_dict()}"

    def __str__(self):
        return self.url()


def pg_db_info(host=None, port=None, name=None, role=None, user=None, password=None, url=None) -> DBUrl:
    dburl = DBUrl(host=host, port=port, name=name, role=role, user=user, password=password, url=url)
    logging.info(f"DATABASE_URL={dburl.copy(password="****")}")
    return dburl


def pg_dsn(db: DBUrl, sa: bool = False) -> DBUrl:
    var = SA_DATABASE_URL if sa else DATABASE_URL
    if sa:
        db = DBUrl(url=getenv(var))
    if not db:
        msg = f"{var} is not configured"
        logging.error(msg)
        raise EnvironmentNotConfigured(msg)
    return db


def pg_execute(cursor, sql: str, *args, **kwargs):
    logging.debug(f"Executing: '{sql}' {args} {kwargs}")
    try:
        cursor.execute(sql, *args, **kwargs)
    except pg.errors.DatabaseError as exc:
        logging.error(f"Error: {exc}")
        raise
    return cursor


def pg_connect(db: DBUrl, sa: bool = False, **kwargs):
    db = pg_dsn(db, sa=sa)
    logging.debug(f"Connecting to dsn: {db.log_url()}")
    conn = pg.connect(db.url(), **kwargs)
    conn.autocommit = kwargs.get("autocommit", True)
    return conn


def pg_count_connections(db: DBUrl, **kwargs) -> int:
    if db.name:
        conn = pg_connect(db, sa=True, **kwargs)
        with conn.cursor() as cursor:
            result = pg_execute(cursor, """SELECT COUNT(*) FROM pg_catalog.pg_stat_activity """ """WHERE datname=%s""", (db.name,)).fetchone()
        conn.close()
        if result:
            return result[0]
    return 0


def pg_clear_connections(db: DBUrl, **kwargs) -> None:
    # Note: this won't work on the sa database, i.e. `postgres`
    if db.name:
        conn = pg_connect(db, sa=True, **kwargs)
        with conn.cursor() as cursor:
            pg_execute(
                cursor,
                """SELECT pg_terminate_backend(pid) FROM pg_catalog.pg_stat_activity """ """WHERE datname = %s""",
                (db.name,),
            )
        conn.close()


def pg_drop_database(db: DBUrl, **kwargs) -> None:
    conn = pg_connect(db, sa=True, **kwargs)
    with conn.cursor() as cursor:
        pg_execute(cursor, f"""DROP DATABASE IF EXISTS {db.name}""")
        pg_execute(cursor, f"""DROP USER IF EXISTS {db.user}""")
        if db.role and db.role != db.user:
            pg_execute(cursor, f"""DROP ROLE IF EXISTS {db.role}""")
    conn.close()
    logging.info(f"""Database '{db.name}' dropped""")


def pg_database_exists(db: DBUrl, silent: bool = False, raise_error: bool = False, **kwargs):
    try:
        conn = pg_connect(db, sa=False, **kwargs)
        conn.close()
        if not silent:
            logging.info(f"""Database '{db.name}' exists""")
        return True
    except pg.errors.DatabaseError as exc:
        if raise_error:
            raise
        if not silent:
            logging.warning(f"""Database '{db.name}': {exc}""")
    if not silent:
        logging.info(f"""Database '{db.name}' does not yet exist or credentials are incorrect""")
    return False


def pg_setup(db: DBUrl, **kwargs):
    conn = pg_connect(db, sa=True, **kwargs)

    with conn.cursor() as cursor:
        with contextlib.suppress(pg.errors.DuplicateObject):
            pg_execute(cursor, f"""CREATE USER {db.user} CREATEDB INHERIT PASSWORD '{db.password}'""")
        if db.role != db.user:
            with contextlib.suppress(pg.errors.DuplicateObject):
                pg_execute(cursor, f"""CREATE ROLE {db.role}""")
            pg_execute(cursor, f"""GRANT {db.role} to {db.user}""")
        pg_execute(cursor, f"""ALTER ROLE {db.role} SET client_encoding to 'utf8'""")
        pg_execute(cursor, f"""ALTER ROLE {db.role} SET default_transaction_isolation to 'read committed'""")
        pg_execute(cursor, f"""ALTER ROLE {db.role} SET timezone to 'UTC'""")
    logging.info(f"""Database '{db.name}' created""")

    with conn.cursor() as cursor:
        with contextlib.suppress(pg.errors.DuplicateDatabase):
            pg_execute(cursor, f"""CREATE DATABASE {db.name} WITH OWNER {db.role}""")
        pg_execute(cursor, f"""GRANT ALL PRIVILEGES ON DATABASE {db.name} TO {db.role}""")

    conn.close()
