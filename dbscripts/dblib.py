import re

import psycopg as pg
from envex import Env

__all__ = (
    'pg_db_info',
    'pg_connect',
    'pg_database_exists',
    'pg_drop_database',
    'pg_setup',
    'pg_dsn',
    'pg_clear_connections',
)


class UnconfiguredEnvironment(BaseException):
    pass


env = Env(readenv=True, parents=True)


def pg_db_info(host=None, port=None, name=None, role=None, user=None, pswd=None, url=None) -> dict:
    db = {
        "scheme": "postgres",
        "host": host or env("DBHOST"),
        "port": port or env("DBPORT"),
        "name": name or env("DBNAME"),
        "user": role or env("DBUSER"),
        "role": user or env("DBROLE", default=env("DBUSER")),
        "pass": pswd or env("DBPASS"),
    }
    if db["host"] is not None and ':' in db["host"]:
        db["host"], db["port"] = db["host"].split(':', maxsplit=1)
    if not url and env.is_set("DATABASE_URL"):
        url = env("DATABASE_URL")
    if url:  # parse it
        p = re.compile(r"""
                       (?P<scheme>[\w+]+)://
                       (?:(?P<user>[^:/]*)(?::(?P<pswd>[^@]*))?@)?
                       (?:(?:\[(?P<ipv6host>[^/?]+)]|(?P<ipv4host>[^/:?]+))?(?::(?P<port>[^/?]*))?)?
                       (?:/(?P<name>[^?]*))?(?:\?(?P<query>.*))?""",
                       re.X,)

        if (m := p.match(url)) is not None:
            for k, v in m.groupdict().items():
                db[k] = v
            db["host"] = db["ipv4host"] or db["ipv6host"]

    db["url"] = f"{db['scheme']}://{db['user']}:{db['pass']}@{db['host']}:{db['port'] or 5432}/{db['name']}"
    return db


def pg_dsn(db, sa=False):
    dsn = env('SA_DATABASE_URL') if sa else db['url']
    if not dsn:
        raise UnconfiguredEnvironment('SA_DATABASE_URL' if sa else 'DATABASE_URL')
    return dsn


def pg_connect(db, sa=False, **kwargs):
    conn = pg.connect(pg_dsn(db, sa=sa), **kwargs)
    conn.autocommit = True
    return conn


def pg_clear_connections(db, **kwargs):
    conn = pg_connect(db, sa=True, **kwargs)
    with conn.cursor() as cursor:
        cursor.execute(f"""SELECT pg_terminate_backend(pid) """
                       f"""FROM postgres.pg_catalog.pg_stat_activity """
                       f"""WHERE datname='{db["name"]}'""")
    conn.close()


def pg_drop_database(db, **kwargs):
    conn = pg_connect(db, sa=True, **kwargs)
    with conn.cursor() as cursor:
        cursor.execute(f"""DROP DATABASE IF EXISTS {db["name"]}""")
        cursor.execute(f"""DROP USER IF EXISTS {db["user"]}""")
        cursor.execute(f"""DROP ROLE IF EXISTS {db["role"]}""")
    conn.close()
    print(f"""Database '{db["name"]}' dropped""")


def pg_database_exists(db, silent=False, **kwargs):
    test_exc = None
    try:
        conn = pg_connect(db, sa=False, **kwargs)
        conn.close()
        if not silent:
            print(f"""Database '{db["name"]}' exists""")
        return True
    except pg.errors.DatabaseError as exc:
        test_exc = exc
    if not silent:
        if test_exc:
            print(f"""Database '{db["name"]}': {test_exc}""")
        print(f"""Database '{db["name"]}' does not yet exist""")
    return False


def pg_setup(db, **kwargs):
    conn = pg_connect(db, sa=True, **kwargs)
    with conn.cursor() as cursor:
        cursor.execute(f"""CREATE ROLE IF NOT EXISTS {db["role"]}""")
        cursor.execute(f"""CREATE USER IF NOT EXISTS {db["user"]} CREATEDB INHERIT PASSWORD '{db["pass"]}'""")
        cursor.execute(f"""GRANT {db["role"]} to {db["user"]}""")
        cursor.execute(f"""ALTER ROLE {db["role"]} SET client_encoding to 'utf8'""")
        cursor.execute(f"""ALTER ROLE {db["role"]} SET default_transaction_isolation to 'read committed'""")
        cursor.execute(f"""ALTER ROLE {db["role"]} SET timezone to 'UTC'""")
    print(f"""Database '{db["name"]}' created""")

    with conn.cursor() as cursor:
        cursor.execute(f"""CREATE DATABASE {db["name"]} WITH OWNER {db["role"]}""")
        cursor.execute(f"""GRANT ALL PRIVILEGES ON DATABASE {db["name"]} TO {db["role"]}""")

    conn.close()
