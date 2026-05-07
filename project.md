# Project Notes

`dbscripts` is a small Python package providing PostgreSQL helper scripts:
`dbutil`, `dbready`, and shared database logic in `dbscripts/dblib.py`.

The package currently supports Python 3.11 and newer. Keep source compatible
with Python 3.11 unless `requires-python` and CI are deliberately updated.

The test suite exercises real PostgreSQL behavior through `testcontainers`, so
Docker must be available for a full test run.

CI is defined in `.github/workflows/build.yml` and tests Python 3.11, 3.12,
3.13, and 3.14.

CI delegates testing and building to:

```yaml
deeprave/python-uv-actions/test-build@v1
```

The `v1` tag is a floating major-version tag and may be updated to the latest
compatible release.
