# ChangeLog

### 2025.2.1

- Adjust create database for aws quirk where owner cannot be directly set but must be assigned after.
- Also adjust remove so that the owner is set to the superuser before dropping the database.

### 2025.2.0

- Avoid using urllib.parse.urlparse for database URL, as it does not handle unusual characters in passwords correctly.

### 2025.1.0

- Switched from poetry to uv for project management.

### 2024.1.0
- Switched to year-semantic versioning
- Additional support for environment variables to set the default variable prefix, now supports ENVPREFIX and uppercased DJANGO_SITE (for my own convenience)

### 1.5.4
- documentation corrections

### 1.5.3
- corrected pyproject.toml to correctly use dbutil.py

### 1.5.2
- added -e <PREFIX> option, to add a prefix to environment variables
- renamed `dbcreate` to `dbutil`, to be more descriptive of function

### 1.5.1 (unpublished)
- various @dependabot dependency updates

### 1.5.0
- updated pre-commit checks
- added unit tests for `dblib.py`
- restructuring and bugfixes
- suppressed exceptions where appropriate
- updated GitHub workflows

### 1.3.1
- back to poetry
- add pre-commit checks

### 1.3.0
- change from poetry to hatch
- add dbready.py
- changed connection logic to allow --host / --port etc to override URL
- print -> logging.info

### 1.2.0
- change driver to psycopg[binary] v3.0

### 1.1.1
- Bug fixes for db exists
