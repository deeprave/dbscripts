from urllib.parse import urlparse, ParseResult

import pytest
from testcontainers.postgres import PostgresContainer
import dbscripts.dblib as dblib
from envex import env

POSTGRES_USER = "postgres"
POSTGRES_PASSWORD = "postgres_password"
POSTGRES_DB = "postgres"
POSTGRES_IMAGE = "postgres:latest"

DB_USER = "test"
DB_PASSWORD = "testing"
DB_NAME = "test_db"


@pytest.fixture(scope="module")
def postgres():
    env("POSTGRES_USER", POSTGRES_USER)
    env("POSTGRES_PASSWORD", POSTGRES_PASSWORD)
    env("POSTGRES_DB", POSTGRES_DB)
    container = PostgresContainer(POSTGRES_IMAGE, driver=None)
    container.start()

    # administator connection
    db_info = dblib.pg_db_info(url=container.get_connection_url())
    db_info.name = "postgres"
    env.set("SA_DATABASE_URL", db_info.url())

    # test connection
    db_info.user = DB_USER
    db_info.password = DB_PASSWORD
    db_info.name = DB_NAME
    env.set("DATABASE_URL", db_info.url())

    yield container
    container.stop()


def test_pg_dsn(postgres):
    db_info = dblib.pg_db_info(url=postgres.get_connection_url())
    dsn = dblib.pg_dsn(db_info)
    assert dsn is not None
    parsed = urlparse(dsn)
    assert isinstance(parsed, ParseResult)


def test_pg_setup(postgres):
    db_info = dblib.pg_db_info(
        url=postgres.get_connection_url(), name=DB_NAME, role=DB_USER, user=DB_USER, password=DB_PASSWORD
    )
    dblib.pg_setup(db_info)  # No assertion, just checking for unexpected exceptions


def test_pg_db_info(postgres):
    db_info = dblib.pg_db_info(
        url=postgres.get_connection_url(), name=DB_NAME, role=DB_USER, user=DB_USER, password=DB_PASSWORD
    )
    assert db_info is not None
    assert isinstance(db_info, dblib.DBUrl)
    assert db_info.host == "localhost"
    assert db_info.user == DB_USER
    assert db_info.password == DB_PASSWORD
    assert db_info.name == DB_NAME


def test_pg_connect(postgres):
    db_info = dblib.pg_db_info(
        url=postgres.get_connection_url(), name=DB_NAME, role=DB_USER, user=DB_USER, password=DB_PASSWORD
    )
    conn = dblib.pg_connect(db_info)
    assert conn is not None
    # additional assertions
    assert not conn.closed


def test_pg_database_exists(postgres):
    db_info = dblib.pg_db_info(
        url=postgres.get_connection_url(), name=DB_NAME, role=DB_USER, user=DB_USER, password=DB_PASSWORD
    )
    exists = dblib.pg_database_exists(db_info)
    assert exists is True


def test_pg_clear_connections(postgres):
    db_info = dblib.pg_db_info(
        url=postgres.get_connection_url(), name=DB_NAME, role=DB_USER, user=DB_USER, password=DB_PASSWORD
    )
    before = dblib.pg_count_connections(db_info)
    dblib.pg_clear_connections(db_info)
    after = dblib.pg_count_connections(db_info)
    assert after == 0, f"Connections not cleared (initial: {before}, final: {after})"


def test_pg_drop_database(postgres):
    db_info = dblib.pg_db_info(
        url=postgres.get_connection_url(), name=DB_NAME, role=DB_USER, user=DB_USER, password=DB_PASSWORD
    )
    dblib.pg_drop_database(db_info)  # No assertion, just checking for exceptions
