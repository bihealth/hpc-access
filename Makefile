.PHONY: serve


manage = python manage.py


serve:
	$(manage) runserver
