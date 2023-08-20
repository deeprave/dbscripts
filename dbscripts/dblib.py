import copy
import logging
import re

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
)


class EnvironmentNotConfigured(BaseException):
    pass


env = Env(readenv=True, parents=True)


class DBUrl:
    def __init__(self, *args, host=None, port=None, name=None, role=None, user=None, pswd=None, url=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.scheme = "postgresql"
        self.host = env("DBHOST")
        self.port = env("DBPORT")
        self.name = env("DBNAME")
        self.user = env("DBUSER")
        self.role = env("DBROLE", default=env("DBUSER"))
        self.pswd = env("DBPASS")
        self.ipv4host = self.ipv6host = ""

        if self.host and ":" in self.host:
            self.host, self.port = self.host.split(":", maxsplit=1)
        if not url and env.is_set("DATABASE_URL"):
            url = env("DATABASE_URL")
        if url:  # parse it
            p = re.compile(
                r"""
                           (?P<scheme>[\w+]+)://
                           (?:(?P<user>[^:/]*)(?::(?P<pswd>[^@]*))?@)?
                           (?:(?:\[(?P<ipv6host>[^/?]+)]|(?P<ipv4host>[^/:?]+))?(?::(?P<port>[^/?]*))?)?
                           (?:/(?P<name>[^?]*))?(?:\?(?P<query>.*))?""",
                re.X,
            )

            if (m := p.match(url)) is not None:
                for k, v in m.groupdict().items():
                    setattr(self, k, v)
                self.host = self.ipv4host or self.ipv6host

        # allow overrides

        if host:
            if ":" in host:
                self.host, self.port = self.host.split(":", maxsplit=1)
            else:
                self.host = host
        if port:
            self.port = port
        if name:
            self.name = name
        if user:
            self.user = user
            if not role:
                self.role = user
        if pswd:
            self.pswd = pswd

    def to_dict(self):
        return dict(
            scheme=self.scheme,
            host=self.host,
            port=self.port,
            name=self.name,
            user=self.user,
            role=self.role,
            pswd=self.pswd,
        )

    def url(self):
        return f"{self.scheme}://{self.user}:{self.pswd}@{self.host}:{self.port or 5432}/{self.name}"

    def __getitem__(self, value):
        if hasattr(self, value):
            return getattr(self, value)
        raise KeyError(value)

    def copy(self):
        return copy.copy(self)


def pg_db_info(host=None, port=None, name=None, role=None, user=None, pswd=None, url=None) -> DBUrl:
    return DBUrl(host=host, port=port, name=name, role=role, user=user, pswd=pswd, url=url)


def pg_dsn(db: DBUrl, sa: bool = False) -> str:
    dsn = env("SA_DATABASE_URL") if sa else db.url()
    if not dsn:
        raise EnvironmentNotConfigured("SA_DATABASE_URL" if sa else "DATABASE_URL")
    return dsn


def pg_connect(db: DBUrl, sa: bool = False, **kwargs):
    conn = pg.connect(pg_dsn(db, sa=sa), **kwargs)
    conn.autocommit = True
    return conn


def pg_clear_connections(db: DBUrl, **kwargs) -> None:
    if db.name:
        conn = pg_connect(db, sa=True, **kwargs)
        with conn.cursor() as cursor:
            cursor.execute(
                f"""SELECT pg_terminate_backend(pid) """
                f"""FROM postgres.pg_catalog.pg_stat_activity """
                f"""WHERE datname='{db.name}'"""
            )
        conn.close()


def pg_drop_database(db: DBUrl, **kwargs) -> None:
    conn = pg_connect(db, sa=True, **kwargs)
    with conn.cursor() as cursor:
        cursor.execute(f"""DROP DATABASE IF EXISTS {db.name}""")
        cursor.execute(f"""DROP USER IF EXISTS {db.user}""")
        if db.role and db.role != db.user:
            cursor.execute(f"""DROP ROLE IF EXISTS {db.role}""")
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
        cursor.execute(f"""CREATE USER {db.user} CREATEDB INHERIT PASSWORD '{db.pswd}'""")
        if db.role != db.user:
            cursor.execute(f"""CREATE ROLE {db.role}""")
            cursor.execute(f"""GRANT {db.role} to {db.user}""")
        cursor.execute(f"""ALTER ROLE {db.role} SET client_encoding to 'utf8'""")
        cursor.execute(f"""ALTER ROLE {db.role} SET default_transaction_isolation to 'read committed'""")
        cursor.execute(f"""ALTER ROLE {db.role} SET timezone to 'UTC'""")
    logging.info(f"""Database '{db.name}' created""")

    with conn.cursor() as cursor:
        cursor.execute(f"""CREATE DATABASE {db.name} WITH OWNER {db.role}""")
        cursor.execute(f"""GRANT ALL PRIVILEGES ON DATABASE {db.name} TO {db.role}""")

    conn.close()
