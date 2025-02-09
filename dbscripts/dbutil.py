#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Create/remove/test database for django using best practices.
"""

import logging
from logging import StreamHandler
import textwrap


from dbscripts.dblib import pg_database_exists, pg_db_info, pg_drop_database, pg_setup, set_env_prefix, set_verbosity


for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)
logging.basicConfig(
    format="%(asctime)s %(levelname)-7s %(message)s",
    level=logging.DEBUG,
    handlers=[StreamHandler()]
)


def main():
    from argparse import ArgumentParser

    parser = ArgumentParser(
        description=__doc__,
        epilog=textwrap.dedent(
            """
        database details are initially sourced from .env which is overridden by the
        command line, by either specifying individual parts or the complete database
        url. superuser account details are sourced from .env in current or parent
        directories only."""
        ),
    )
    parser.add_argument("-c", "--create", action="store_true", default=False, help="Create the database")
    parser.add_argument(
        "-r",
        "--remove",
        action="store_true",
        default=False,
        help="Completely remove the database and associated users/roles",
    )
    parser.add_argument(
        "-t", "--test", action="store_true", default=False, help="Test to see if the database and roles exist"
    )
    parser.add_argument("-u", "--url", default=None, help="Connection url: postgresql://host[:port]/database")
    parser.add_argument("-v", "--verbose", action="count", default=0, help="Increase verbosity")
    parser.add_argument("-e", "--prefix", default=None, help="set a prefix for environment variables")
    parser.add_argument("-H", "--host", default=None, help="override database hostname")
    parser.add_argument("-P", "--port", default=None, help="override database port")
    parser.add_argument("-N", "--name", default=None, help="override database name")
    parser.add_argument("-R", "--role", default=None, help="override database owner role")
    parser.add_argument("-U", "--user", default=None, help="override database username")
    parser.add_argument("-p", "--pswd", default=None, help="override database password")
    a = parser.parse_args()

    set_env_prefix(a.prefix)

    dbi = pg_db_info(host=a.host, port=a.port, name=a.name, role=a.role, user=a.user, password=a.pswd, url=a.url)

    set_verbosity(a.verbose)

    if a.test:
        pg_database_exists(dbi)
    elif a.remove:
        pg_drop_database(dbi)
    elif pg_database_exists(dbi, silent=not a.verbose):
        logging.warning(f"Database {dbi.name} already exists")
    elif a.create:
        pg_setup(dbi)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
