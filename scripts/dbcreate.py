#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Create/remove/test for database for django using best practices.
"""
import re
import textwrap

import psycopg2 as pg
from envex import Env


class UnconfiguredEnvironment(BaseException):
    pass


env = Env(readenv=True, parents=True)


def db_info(host=None, port=None, name=None, role=None,  user=None, pswd=None, url=None) -> dict:
    db = {
        "scheme": "postgres",
        "host": host or env("DBHOST"),
        "port": port or env("DBPORT"),
        "name": name or env("DBNAME"),
        "user": role or env("DBUSER"),
        "role": user or env("DBROLE", default=env("DBUSER")),
        "pass": pswd or env("DBPASS"),
    }
    if not url and env.is_set("DATABASE_URL"):
        url = env("DATABASE_URL")
    if url: # parse it
        p = re.compile(r"""
                       (?P<scheme>[\w\+]+)://
                       (?:(?P<user>[^:/]*)(?::(?P<pswd>[^@]*))?@)?
                       (?:(?:\[(?P<ipv6host>[^/\?]+)\]|(?P<ipv4host>[^/:\?]+))?(?::(?P<port>[^/\?]*))?)?
                       (?:/(?P<name>[^\?]*))?(?:\?(?P<query>.*))?""",
                       re.X,)
        m = m = p.match(url)
        if m is not None:
            for k, v in m.groupdict().items():
                db[k] = v
            db["host"] = db["ipv4host"] or db["ipv6host"]

    db["url"] = f"{db['scheme']}://{db['user']}@{db['pass']}:info['host']:{db['port'] or 5432}/{db['name']}"
    return db


def pg_dsn(db, sa=False):
    dsn = env('SA_DATABASE_URL') if sa else db['url']
    if not dsn:
        raise UnconfiguredEnvironment('SA_DATABASE_URL' if sa else 'DATABASE_URL')
    return dsn


def db_connect(db, sa=False, **kwargs):
    conn = pg.connect(pg_dsn(db, sa=sa), **kwargs)
    conn.autocommit = True
    return conn


def clear_connections(db, **kwargs):
    conn = db_connect(db, sa=True, **kwargs)
    with conn.cursor() as cursor:
        cursor.execute(f"""SELECT pg_terminate_backend(pid) """
                       f"""FROM postgres.pg_catalog.pg_stat_activity """
                       f"""WHERE datname='{db["name"]}'""")
    conn.close()


def drop_db(db, **kwargs):
    conn = db_connect(db, sa=True, **kwargs)
    with conn.cursor() as cursor:
        cursor.execute(f"""DROP DATABASE IF EXISTS {db["name"]}""")
        cursor.execute(f"""DROP USER IF EXISTS {db["user"]}""")
        cursor.execute(f"""DROP ROLE IF EXISTS {db["role"]}""")
    conn.close()
    print(f"""Database '{db["name"]}' dropped""")


def setup_db(db, **kwargs):
    conn = db_connect(db, sa=True, **kwargs)
    with conn.cursor() as cursor:
        cursor.execute(f"""CREATE ROLE {db["role"]}""")
        cursor.execute(f"""CREATE USER {db["user"]} CREATEDB INHERIT PASSWORD '{db["pass"]}'""")
        cursor.execute(f"""GRANT {db["role"]} to {db["user"]}""")
        cursor.execute(f"""ALTER ROLE {db["role"]} SET client_encoding to 'utf8'""")
        cursor.execute(f"""ALTER ROLE {db["role"]} SET default_transaction_isolation to 'read committed'""")
        cursor.execute(f"""ALTER ROLE {db["role"]} SET timezone to 'UTC'""")
    print(f"""Database '{db["name"]}' created""")

    with conn.cursor() as cursor:
        cursor.execute(f"""CREATE DATABASE {db["name"]} WITH OWNER {db["role"]}""")
        cursor.execute(f"""GRANT ALL PRIVILEGES ON DATABASE {db["name"]} TO {db["role"]}""")

    conn.close()


def test_db(db, silent=False, **kwargs):
    try:
        conn = db_connect(db, sa=False, **kwargs)
        conn.close()
        if not silent:
            print(f"""Database '{db["name"]}' exists""")
        return True
    except pg.DatabaseError:
        pass
    if not silent:
        print(f"""Database '{db["name"]}' does not yet exist""")
    return False


if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser(description=__doc__, epilog=textwrap.dedent("""
        detabase details are initially sourced from .env which is overridden by the
        command line, by either specifying individual parts or the complete database
        url. superuser account details are sourced from .env in current or parent 
        directories only."""))
    parser.add_argument('-c', '--create', action='store_true', default=False,
                        help='Create the database')
    parser.add_argument('-r', '--remove', action='store_true', default=False,
                        help='Completely remove the database and associated users/roles')
    parser.add_argument('-t', '--test', action='store_true', default=False,
                        help='Test to see if the database and roles exist')
    parser.add_argument('-H', '--host', default=None, help='database hostname')
    parser.add_argument('-P', '--port', default=None, help='database port')
    parser.add_argument('-n', '--name', default=None, help='database name')
    parser.add_argument('-R', '--role', default=None, help='database owner role')
    parser.add_argument('-u', '--user', default=None, help='database username')
    parser.add_argument('-p', '--pswd', default=None, help='database password')
    parser.add_argument('-U', '--url', default=None, help='database url (overrides all of the above)')
    a = parser.parse_args()

    dbi = db_info(host=a.host, port=a.port, name=a.name, role=a.role,  user=a.user, pswd=a.pswd, url=a.url)

    if a.test:
        test_db(dbi)
    else:
        if a.remove:
            drop_db(dbi)
        elif test_db(dbi, silent=True):
            print(f"Database {dbi['name']} already exists")
            parser.print_help()
        elif a.create:
            setup_db(dbi)
        else:
            parser.print_help()
