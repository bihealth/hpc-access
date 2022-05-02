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
- Fixed CDN include feature

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
- Added models for HPC projects and project requests (#4)
- Added HPC project detail view (#8)
- Added HPC project create request views (#8)
- Added representation to HPC group, user and project model (#79)
- Comment fields are optional for non-admins (#77)
- Form field ``resources_requested`` is hidden and content compiled from from additional ``tier1`` and ``tier2`` fields (#77)
- Form field ``members`` is hidden and collected from a dropdown field with add button (#77)
- Form field ``expiration`` is hidden and gets a default of +1 year (#77)
- Owner and delegate automatically  added to ``members`` field (#77)
- Added consent button to group request form (#77)
- Revised texts in forms and added info texts on user actions (#87)
- Added models for group and project invitations (#91)
- User can accept or reject a group invitation before potentially creating the user (#91)
- User can accept or reject a project invitation before potentially joining the group (#91)
- Created HPC group change request models, views and rules (#54)
- Created HPC user change request models, views and rules (#55)
- Created HPC project change request models, views and rules (#85, #103)
- Added check for existing users and project to HpcUser and HpcProject create requests (#89)
- Extended email notifications (#76)

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
- Added HPC project detail view (#8)
- Added HPC project create request views (#8)
- Fixed bug where creating HPC project didn't add members to version object (#79)
- Fixed bug where creating HPC group didn't add owner to version object (#79)
- ``HpcUser`` is not created upon accepting a user request, but an ``HpcGroupInvitation`` object (#91)
- Accepting a project create request creates an ``HpcProjectInvitation`` object for each requested member (#91)
- Created HPC group change request views and rules (#54)
- Created HPC user change request views and rules (#55)
- Created HPC project change request views and rules (#85)
- Extended email notifications (#76)
