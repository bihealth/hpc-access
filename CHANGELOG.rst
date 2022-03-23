HPC Access Changelog
^^^^^^^^^^^^^^^^^^^^

Changelog for the **HPC Access** Django app package.
Loosely follows the `Keep a Changelog <http://keepachangelog.com/en/1.0.0/>`_ guidelines.


HEAD (unreleased)
=================

General
-------

- Django 4 codebase created, using Bootstrap 5 and Python 3.10
- Added Sentry support
- Added Docker support
- Added ``rules`` package dependency (#9)
- Added codacy integration (#6)
- Reworked github CI workflow (#6)

UserSec
-------

- App created
- Created login page with LDAP support (#2)
- Created models for users, groups and requests (#3)
- Created rules and permissions (#9)
- Created orphan view, added factories and tests (#5)
- Created progressing user view (#6)
- Created group request view (#7)

AdminSec
--------

- App created
