# DbScripts

A collection of scripts for database management.

Designed for use with postgresql.

## dbcreate

```shell
usage: dbcreate.py [-h] [-c] [-r] [-t] [-u URL] [-v VERBOSE] [-H HOST] [-P PORT] [-N NAME] [-R ROLE] [-U USER] [-p PSWD]

Create/remove/test for database for django using best practices.

options:
  -h, --help            show this help message and exit
  -c, --create          Create the database
  -r, --remove          Completely remove the database and associated users/roles
  -t, --test            Test to see if the database and roles exist
  -u URL, --url URL     Connection url: postgresql://host[:port]/database
  -v VERBOSE, --verbose VERBOSE
                        Verbose output
  -H HOST, --host HOST  override database hostname
  -P PORT, --port PORT  override database port
  -N NAME, --name NAME  override database name
  -R ROLE, --role ROLE  override database owner role
  -U USER, --user USER  override database username
  -p PSWD, --pswd PSWD  override database password

database details are initially sourced from .env which can be overridden by the command line, either by specifying individual parts or the complete database url. superuser account details are sourced from .env in current or parent directories only.
```

## dbready

```shell
usage: dbready.py [-h] [-w] [-t TIMEOUT] [-s SLEEP] [-d] [-q] [-u [URL]] [-v] [-H [HOST]] [-P [PORT]] [-N [NAME]] [-U [USER]] [-p [PSWD]]

test for database ready and optionally connection

options:
  -h, --help            show this help message and exit
  -w, --wait            Wait until ready
  -t TIMEOUT, --timeout TIMEOUT
                        Wait timeout (0=infinite)
  -s SLEEP, --sleep SLEEP
                        Sleep time between retries
  -d, --database        Test to see if the database exists (not just connect)
  -q, --quiet           Do not report errors or progress
  -u [URL], --url [URL]
                        Connection url: postgresql://host[:port]/database
  -v, --verbose         Verbose output
  -H [HOST], --host [HOST]
                        override database hostname
  -P [PORT], --port [PORT]
                        override database port
  -N [NAME], --name [NAME]
                        override database name
  -U [USER], --user [USER]
                        override database username
  -p [PSWD], --pswd [PSWD]
                        override database password

```

## Rationale
Many web developers undertake numerous projects that necessitate the use of a database, with a significant majority favoring PostgreSQL.

This toolkit provides a streamlined approach to database management, adhering to industry best practices.
It guarantees that:
- The user affiliated with an application is not a superuser.
- The user affiliated with an application is secured with a password.
- The user inherits access to the database from a nologin role, which actually owns the database
- Tables, sequences and other entities are not created in the superuser `postgres` database, to better support multi-tenancy with other applications.
- Database metadata including credentials is placed within a `.env` file, or since 1.4 also supports fetching secrets from hashicorp vault.
