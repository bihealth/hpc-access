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
- Added ``popper.js`` library for tooltip support (#64)
- Added ldap3 dependency (#60)

UserSec
-------

- App created
- Created login page with LDAP support (#2)
- Created models for users, groups and requests (#3)
- Created rules and permissions (#9)
- Created orphan view, added factories and tests (#5)
- Created progressing user view (#6)
- Created group create request view (#7)
- Added ``editor`` field to request models (#37)
- Created HPC user overview view (#13)
- Created HPC group detail view (#53)
- Registered models with admin site (#53)
- Created HPC user create request views (#58)
- Reworked overview page (#64)
- Created HPC user detail view (#60)
- Disentagle and modularize html templates (#69)

AdminSec
--------

- App created
- Created overview view (#37)
- Created functionality to accept group create requests (#37)
- Created HPC admin flag for user and added permission (#37)
- Accepting group create request creates HPC user and group (#13)
- Created HPC user create request views (#58)
- Reworked overview page (#64)
- Created HPC user detail view (#60)
- Created HPC group detail view (#60)
- Added logic for approving HPC user create request (#60)
- Added LDAP Connector class to fetch username by email alongside LDAP authentication (#60)
- Enabled email sending when HPC user create request is accepted (#60)
