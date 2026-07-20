manage = uv run python manage.py

# Argument passed from commandline, optional for some rules, mandatory for others.
arg =


.PHONY: serve
serve:
	$(manage) runserver


.PHONY: serve-public
serve-public:
	$(manage) runserver 0.0.0.0:8000


.PHONY: celery
celery:
	uv run celery -A config.celery_app worker -l info --beat


.PHONY: test
test:
	ENABLE_LDAP=0 ENABLE_LDAP_SECONDARY=0 $(manage) test -v2 --settings=config.settings.test


.PHONY: test-keepdb
test-keepdb:
	ENABLE_LDAP=0 ENABLE_LDAP_SECONDARY=0 $(manage) test -v2 --settings=config.settings.test --keepdb


.PHONY: _test-snap
_test-snap:
	ENABLE_LDAP=0 ENABLE_LDAP_SECONDARY=0 $(manage) test -v2 --settings=config.settings.test --keepdb --snapshot-update usersec.tests.test_serializers adminsec.tests.test_views_api


.PHONY: test-snap
test-snap: _test-snap format


.PHONY: lint
lint:
	uv run ruff check
	uv run ruff format --check


.PHONY: format
format:
	uv run ruff format
	uv run ruff check --fix


.PHONY: migrations
migrations:
	$(manage) makemigrations


.PHONY: _migrate
_migrate: migrations
	$(manage) migrate


.PHONY: migrate
migrate: _migrate format


.PHONY: test-coverage
test-coverage:
	uv run coverage run --source=adminsec,usersec --omit={adminsec,usersec}/migrations/*,*.html manage.py test -v2 --settings=config.settings.test
	uv run coverage report
	uv run coverage html


.PHONY: test-coverage-keepdb
test-coverage-keepdb:
	uv run coverage run --source=adminsec,usersec --omit={adminsec,usersec}/migrations/*,*.html manage.py test -v2 --settings=config.settings.test --keepdb
	uv run coverage report
	uv run coverage html
