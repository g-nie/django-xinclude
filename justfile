default:
    just --list

@test *options:
    python -m pytest --ds=tests.settings {{ options }}

@coverage:
    coverage erase
    coverage run -m django test --settings=tests.settings --pythonpath=.
    coverage report
