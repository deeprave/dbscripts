#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test for database ready and optionally connection
"""

import logging
import textwrap
import time
from argparse import ArgumentParser

from psycopg import DatabaseError

from dbscripts.dblib import pg_connect, pg_database_exists, pg_db_info, set_env_prefix

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s %(levelname)-7s %(message)s", handlers=[logging.StreamHandler()]
)


def main():
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
    parser.add_argument("-w", "--wait", action="store_true", default=False, help="Wait until ready")
    parser.add_argument("-t", "--timeout", action="store", type=float, default=0.0, help="Wait timeout (0=infinite)")
    parser.add_argument("-s", "--sleep", action="store", type=float, default=2.0, help="Sleep time between retries")
    parser.add_argument(
        "-d",
        "--database",
        action="store_true",
        default=False,
        help="Test to see if the database exists (not just connect)",
    )
    parser.add_argument("-q", "--quiet", action="store_true", default=False, help="Do not report errors or progress")
    parser.add_argument("-u", "--url", nargs="?", default="", help="Connection url: postgresql://host[:port]/database")
    parser.add_argument("-e", "--prefix", nargs="?", default=None, help="set a prefix for environment variables")
    parser.add_argument("-v", "--verbose", action="store_true", default=False, help="Verbose output")
    parser.add_argument("-H", "--host", nargs="?", default="", help="override database hostname")
    parser.add_argument("-P", "--port", nargs="?", default="", help="override database port")
    parser.add_argument("-N", "--name", nargs="?", default="", help="override database name")
    parser.add_argument("-U", "--user", nargs="?", default="", help="override database username")
    parser.add_argument("-p", "--pswd", nargs="?", default="", help="override database password")

    a = parser.parse_args()

    if a.prefix:
        set_env_prefix(a.prefix)

    dbi = pg_db_info(host=a.host, port=a.port, name=a.name, role=a.user, user=a.user, password=a.pswd, url=a.url)

    db = dbi.copy()
    db.name = ""

    if a.verbose:
        dbc = dbi.copy()
        dbc.password = "********"
        logging.info(f"DATABASE_URL={dbc.url()}")

    now = time.time()
    end_at = now
    end_at = end_at + a.timeout if a.timeout else -1

    count = 0
    success = False
    while not success and end_at > 0 or end_at <= now:
        count += 1
        try:
            conn = pg_connect(db)
            conn.close()
            success = True
        except DatabaseError as exc:
            message = str(exc.args[0]).replace("\n", " ")
            success = all(reason not in message for reason in ["Connection refused", "connection is bad"])
            if not a.quiet and a.verbose:
                logging.warning(message)

        if success:
            break

        if not a.wait:
            break

        now = time.time()
        if a.verbose:
            logging.info(f"Database is not ready ({count})")
        time.sleep(a.sleep)

    if not success:
        if not a.quiet:
            logging.info("Database is NOT available for connections")
        exit(1)

    if a.database:
        if pg_database_exists(dbi, silent=a.quiet):
            if not a.quiet:
                logging.info(f"Database '{dbi['name']}' exists and credentials are correct")
        else:
            exit(2)

    elif not a.quiet and a.verbose:
        logging.info("Database is available and accepting connections")

    exit(0)


if __name__ == "__main__":
    main()
