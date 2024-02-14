manage = python manage.py

# Argument passed from commandline, optional for some rules, mandatory for others.
arg =


.PHONY: serve
serve:
	$(manage) runserver

celery:
	celery -A config.celery_app worker -l info --beat


.PHONY: lack
black:
	black . -l 100 --exclude '/(\.eggs|\.git|\.hg|\.mypy_cache|\.nox|\.tox|\.?v?env|_build|buck-out|build|dist|src)/' $(arg)


.PHONY: test
test:
	ENABLE_LDAP=0 ENABLE_LDAP_SECONDARY=0 $(manage) test -v2 --settings=config.settings.test


.PHONY: test-keepdb
test-keepdb:
	ENABLE_LDAP=0 ENABLE_LDAP_SECONDARY=0 $(manage) test -v2 --settings=config.settings.test --keepdb


.PHONY: test-snap
test-snap:
	ENABLE_LDAP=0 ENABLE_LDAP_SECONDARY=0 $(manage) test -v2 --settings=config.settings.test --keepdb usersec.tests.test_serializers adminsec.tests.test_views_api


.PHONY: isort
isort:
	isort --force-sort-within-sections --profile=black .

