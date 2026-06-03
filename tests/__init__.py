# Marks tests/ as a package so `from tests.conftest import ...` resolves
# consistently (pytest inserts the repo root on sys.path for the package).
