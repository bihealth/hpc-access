.PHONY: serve


manage = python manage.py


serve:
	$(manage) runserver


black:
	black -l 100 --exclude '/(\.eggs|\.git|\.hg|\.mypy_cache|\.nox|\.tox|\.?v?env|_build|buck-out|build|dist|src)/' .
