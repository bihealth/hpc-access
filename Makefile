.PHONY: serve


manage = python manage.py

# Argument passed from commandline, optional for some rules, mandatory for others.
arg =


serve:
	$(manage) runserver


black:
	black . -l 100 --exclude '/(\.eggs|\.git|\.hg|\.mypy_cache|\.nox|\.tox|\.?v?env|_build|buck-out|build|dist|src)/' $(arg)


test:
	ENABLE_LDAP=0 ENABLE_LDAP_SECONDARY=0 $(manage) test -v2 --settings=config.settings.test

