# ChangeLog
### 1.5.2
- added -e <PREFIX> option, to add a prefix to environment variables 
- renamed `dbcreate` to `dbutil`, to be more descriptive of function

### 1.5.2 (unpublished)
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
