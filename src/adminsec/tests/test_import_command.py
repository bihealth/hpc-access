"""Database tests for the ``import`` management command.

Run with ``./manage.py test -v2 adminsec.tests.test_import_command`` (adjust
the module path to where this file is installed). Requires the project's
normal test database, including django-pghistory triggers.
"""

import importlib
import json
import re
import tempfile
import uuid
from io import StringIO
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.utils.dateparse import parse_datetime

from usersec.models import (
    OBJECT_STATUS_ACTIVE,
    OBJECT_STATUS_DELETED,
    HpcGroup,
    HpcProject,
    HpcUser,
)

User = get_user_model()

COMMAND = "import"
COMMAND_MODULE = importlib.import_module("adminsec.management.commands.import")
NS = uuid.UUID("12345678-1234-5678-1234-567812345678")


# ------------------------------------------------------------------------------
# Helpers to build a cluster-state.json document
# ------------------------------------------------------------------------------


class State:
    """Builds a cluster-state document using readable keys instead of UUIDs.

    ``salt`` changes every generated UUID, which simulates a fresh export where
    the (arbitrary) UUIDs of the json file are unrelated to those of the last one.
    """

    def __init__(self, salt=""):
        self.salt = salt
        self.users, self.groups, self.projects = {}, {}, {}
        self._uid = 5000

    def user(self, key, username, primary_group=None, **kw):
        self._uid += 1
        self.users[key] = {
            "username": username,
            "first_name": key.title(),
            "last_name": "Tester",
            "full_name": f"{key.title()} Tester",
            "display_name": f"{key.title()} T.",
            "email": f"{key}@example.com",
            "phone_number": "+49 30 000",
            "resources_requested": {"tier1_home": 1},
            "resources_used": {"tier1_home": 0},
            "status": "ACTIVE",
            "home_directory": f"/data/home/{username}",
            "login_shell": "/usr/bin/bash",
            "uid": self._uid,
            "expiration": "2030-01-01T00:00:00+00:00",
            "primary_group": primary_group,  # key of a group (or project)
            **kw,
        }
        return self

    def group(self, key, gid, owner, delegate=None, **kw):
        self.groups[key] = {
            "name": f"grp-{key}",
            "description": "a group",
            "owner": owner,  # user key
            "delegate": delegate,  # user key or None
            "status": "ACTIVE",
            "gid": gid,
            "folders": {"tier1_work": f"/data/work/grp-{key}"},
            "resources_requested": {"tier1_work": 10},
            "resources_used": {"tier1_work": 1},
            "expiration": "2030-01-01T00:00:00+00:00",
            **kw,
        }
        return self

    def project(self, key, name, gid, group, members=(), delegate=None, **kw):
        self.projects[key] = {
            "name": name,
            "gid": gid,
            "group": group,  # group key
            "delegate": delegate,  # user key or None
            "members": list(members),  # user keys
            "status": "ACTIVE",
            "folders": {"tier1_work": f"/data/work/{name}"},
            "resources_requested": {"tier1_work": 5},
            "resources_used": {"tier1_work": 1},
            "expiration": "2030-01-01T00:00:00+00:00",
            **kw,
        }
        return self

    def _id(self, key):
        return str(uuid.uuid5(NS, self.salt + key)) if key else None

    def to_dict(self):
        users = {}
        for key, d in self.users.items():
            d = dict(d)
            d["primary_group"] = self._id(d["primary_group"]) if d["primary_group"] else None
            users[self._id(key)] = d
        groups = {}
        for key, d in self.groups.items():
            d = dict(d, owner=self._id(d["owner"]), delegate=self._id(d["delegate"]))
            groups[self._id(key)] = d
        projects = {}
        for key, d in self.projects.items():
            d = dict(
                d,
                group=self._id(d["group"]),
                delegate=self._id(d["delegate"]),
                members=[self._id(m) for m in d["members"]],
            )
            projects[self._id(key)] = d
        return {"hpc_users": users, "hpc_groups": groups, "hpc_projects": projects}


def baseline(salt=""):
    """alice owns g1 (delegate bob), dave owns g2, carol is an alumna, p1 in g1."""
    return (
        State(salt)
        .user("alice", "alice_c", primary_group="g1")
        .user("bob", "bob_c", primary_group="g1")
        .user("carol", "carol_m")
        .user("dave", "dave_c", primary_group="g2")
        .group("g1", gid=1001, owner="alice", delegate="bob")
        .group("g2", gid=1002, owner="dave")
        .project("p1", "proj1", gid=2001, group="g1", members=["alice", "bob"], delegate="bob")
    )


def summary(out):
    """Parse the command's report into {section: {label: count}}."""
    result, section = {}, None
    for line in out.splitlines():
        if m := re.match(r"--- (\w+) updates ---", line):
            section = result.setdefault(m.group(1), {})
        elif section is not None and (m := re.match(r" \* (\d+) (\w+)", line)):
            section[m.group(2)] = int(m.group(1))
    return result


# ------------------------------------------------------------------------------
# Test cases
# ------------------------------------------------------------------------------


class ImportCommandTestBase(TestCase):
    def setUp(self):
        super().setUp()
        self.worker, _ = User.objects.get_or_create(username="hpc-worker")

    def run_import(self, state, *args, force=False, answer="y", stdout=None, stderr=None):
        """Confirm ordinary imports; use force explicitly when testing its guardrail.

        Caller-supplied streams remain available when the command raises.
        """
        doc = state.to_dict() if isinstance(state, State) else state
        out = stdout if stdout is not None else StringIO()
        err = stderr if stderr is not None else StringIO()
        with tempfile.NamedTemporaryFile("w", suffix=".json") as fp:
            json.dump(doc, fp)
            fp.flush()
            extra = ["--force"] if force else []
            with mock.patch("builtins.input", return_value=answer) as prompt:
                try:
                    call_command(COMMAND, fp.name, *extra, *args, stdout=out, stderr=err)
                finally:
                    if force:
                        prompt.assert_not_called()
            if not force:
                prompt.assert_called_once()
        return out.getvalue(), err.getvalue()

    def db_snapshot(self):
        """Capture all concrete fields and memberships, including soft deletes."""
        return {
            "rows": {
                model._meta.label: list(model.objects.order_by("pk").values())
                for model in (User, HpcUser, HpcGroup, HpcProject)
            },
            "members": {
                project.pk: list(project.members.order_by("pk").values_list("pk", flat=True))
                for project in HpcProject.objects.order_by("pk")
            },
        }


class TestInitialImport(ImportCommandTestBase):
    def test_creates_all_objects_and_foreign_keys(self):
        out, _ = self.run_import(baseline())

        self.assertEqual(summary(out)["User"]["added"], 4)
        self.assertEqual(HpcUser.objects.count(), 4)
        self.assertEqual(HpcGroup.objects.count(), 2)
        self.assertEqual(HpcProject.objects.count(), 1)

        # Django users: suffix mapping, defaults for fields missing in the json
        alice_u = User.objects.get(username="alice@CHARITE")
        self.assertEqual(alice_u.email, "alice@example.com")
        self.assertEqual(alice_u.name, "Alice Tester")
        self.assertFalse(alice_u.consented_to_terms)
        self.assertFalse(alice_u.is_staff or alice_u.is_superuser or alice_u.is_hpcadmin)
        self.assertTrue(User.objects.filter(username="carol@MDC-BERLIN").exists())

        alice, bob = HpcUser.objects.get(username="alice_c"), HpcUser.objects.get(username="bob_c")
        carol = HpcUser.objects.get(username="carol_m")
        g1 = HpcGroup.objects.get(gid=1001)

        # HpcUser -> User / creator
        self.assertEqual(alice.user, alice_u)
        self.assertEqual(carol.user.username, "carol@MDC-BERLIN")
        self.assertEqual(alice.creator, self.worker)

        # Primary groups are stored as GIDs, independent of group/project UUIDs.
        self.assertEqual(alice.primary_group_gid, g1.gid)
        self.assertEqual(bob.primary_group_gid, g1.gid)
        self.assertIsNone(carol.primary_group_gid)
        self.assertEqual(g1.owner, alice)
        self.assertEqual(g1.delegate, bob)
        self.assertIsNone(HpcGroup.objects.get(gid=1002).delegate)
        self.assertEqual(g1.creator, self.worker)

        # Project
        p1 = HpcProject.objects.get(name="proj1")
        self.assertEqual(p1.group, g1)
        self.assertEqual(p1.delegate, bob)
        self.assertEqual({m.username for m in p1.members.all()}, {"alice_c", "bob_c"})

    def test_creates_history_events(self):
        """django-pghistory records at least one event per imported object."""
        self.run_import(baseline())
        for obj in (
            HpcUser.objects.get(username="alice_c"),
            HpcGroup.objects.get(gid=1001),
            HpcProject.objects.get(name="proj1"),
        ):
            self.assertGreaterEqual(obj.events.count(), 1, obj)

    def test_names_are_stripped_and_empty_values_tolerated(self):
        s = baseline()
        s.users["carol"].update(
            first_name="  Carol ", last_name=None, full_name=" Carol X ", display_name=None
        )
        self.run_import(s)
        u = User.objects.get(username="carol@MDC-BERLIN")
        self.assertEqual((u.first_name, u.last_name), ("Carol", ""))
        self.assertEqual((u.name, u.display_name), ("Carol X", ""))

    def test_primary_group_can_point_to_project(self):
        s = baseline()
        s.users["carol"]["primary_group"] = "p1"
        _, err = self.run_import(s)
        self.assertEqual(HpcUser.objects.get(username="carol_m").primary_group_gid, 2001)
        self.assertEqual(err, "")


class TestIdempotencyAndKeys(ImportCommandTestBase):
    def test_reimport_of_same_file_changes_nothing(self):
        self.run_import(baseline())
        before = self.db_snapshot()
        out, err = self.run_import(baseline())
        self.assertEqual(self.db_snapshot(), before)
        for name, counts in summary(out).items():
            self.assertEqual(
                (counts["added"], counts["removed"], counts["changed"]), (0, 0, 0), name
            )
        self.assertEqual(err, "")

    def test_json_uuids_are_irrelevant_for_existing_objects(self):
        """Objects are matched by username/gid/name, never by the json UUIDs."""
        self.run_import(baseline(salt="first-export"))
        before = self.db_snapshot()
        uuids_before = set(HpcUser.objects.values_list("uuid", flat=True))

        out, _ = self.run_import(baseline(salt="second-export"))

        self.assertEqual(self.db_snapshot(), before)  # same pks, same rows
        self.assertEqual(set(HpcUser.objects.values_list("uuid", flat=True)), uuids_before)
        self.assertEqual(summary(out)["HpcGroup"]["added"], 0)
        # relationships survive
        self.assertEqual(HpcGroup.objects.get(gid=1001).owner.username, "alice_c")
        self.assertEqual(HpcProject.objects.get(name="proj1").members.count(), 2)

    def test_member_order_does_not_count_as_a_change(self):
        self.run_import(baseline())
        s = baseline()
        s.projects["p1"]["members"].reverse()
        out, _ = self.run_import(s, force=True)
        self.assertEqual(summary(out)["HpcProject"]["changed"], 0)

    def test_existing_account_without_hpc_user_is_reused(self):
        account = User.objects.create(
            username="alice@CHARITE", email="old@example.com", consented_to_terms=True
        )
        self.run_import(baseline())
        account.refresh_from_db()
        self.assertEqual(account.email, "alice@example.com")
        self.assertTrue(account.consented_to_terms)
        self.assertEqual(HpcUser.objects.get(username="alice_c").user_id, account.pk)


class TestUpdates(ImportCommandTestBase):
    def setUp(self):
        super().setUp()
        self.run_import(baseline())

    def test_hpc_user_fields_updated_but_expiration_and_consent_preserved(self):
        HpcUser.objects.filter(username="bob_c").update(expiration="2099-12-31T00:00:00Z")
        User.objects.filter(username="bob@CHARITE").update(consented_to_terms=True)
        events_before = HpcUser.objects.get(username="bob_c").events.count()
        s = baseline()
        s.users["bob"].update(
            uid=9999,
            status="EXPIRED",
            login_shell="/usr/bin/zsh",
            home_directory="/new/home",
            resources_requested={"tier1_home": 7},
            resources_used={"tier1_home": 3},
            expiration="2001-01-01T00:00:00+00:00",
        )
        out, _ = self.run_import(s)

        self.assertEqual(summary(out)["HpcUser"]["changed"], 1)
        bob = HpcUser.objects.get(username="bob_c")
        self.assertEqual(
            (bob.uid, bob.status, bob.login_shell, bob.home_directory),
            (9999, "EXPIRED", "/usr/bin/zsh", "/new/home"),
        )
        self.assertEqual(bob.resources_requested, {"tier1_home": 7})
        self.assertEqual(bob.resources_used, {"tier1_home": 3})
        self.assertEqual(bob.expiration, parse_datetime("2099-12-31T00:00:00Z"))
        self.assertGreater(bob.events.count(), events_before)
        self.assertTrue(User.objects.get(username="bob@CHARITE").consented_to_terms)

    def test_django_user_fields_updated(self):
        s = baseline()
        s.users["alice"].update(
            email="new@example.com",
            phone_number="123",
            full_name="A. T.",
            first_name=" Alicia ",
            last_name=" Test ",
            display_name=" A ",
        )
        out, _ = self.run_import(s)
        self.assertEqual(summary(out)["User"]["changed"], 1)
        u = User.objects.get(username="alice@CHARITE")
        self.assertEqual((u.email, u.phone, u.name), ("new@example.com", "123", "A. T."))
        self.assertEqual((u.first_name, u.last_name, u.display_name), ("Alicia", "Test", "A"))

    def test_inactive_account_is_updated_with_warning_without_reactivation(self):
        User.objects.filter(username="bob@CHARITE").update(is_active=False)
        s = baseline()
        s.users["bob"]["email"] = "new@example.com"
        _, err = self.run_import(s)
        bob = User.objects.get(username="bob@CHARITE")
        self.assertFalse(bob.is_active)
        self.assertEqual(bob.email, "new@example.com")
        self.assertIn('Warning: user "bob@CHARITE" is not active', err)

    def test_primary_group_moves_to_project_and_tracks_its_gid(self):
        s = baseline()
        s.users["dave"]["primary_group"] = "p1"
        self.run_import(s)
        self.assertEqual(HpcUser.objects.get(username="dave_c").primary_group_gid, 2001)
        s.projects["p1"]["gid"] = 2999
        self.run_import(s)
        self.assertEqual(HpcUser.objects.get(username="dave_c").primary_group_gid, 2999)
        self.assertEqual(HpcProject.objects.get(name="proj1").gid, 2999)

    def test_missing_primary_group_reports_and_skips_hpc_user_update(self):
        s = baseline()
        s.users["dave"].update(primary_group="missing", uid=9999)
        before = HpcUser.objects.get(username="dave_c")
        out, err = self.run_import(s)
        dave = HpcUser.objects.get(username="dave_c")
        self.assertEqual((dave.uid, dave.primary_group_gid), (before.uid, before.primary_group_gid))
        self.assertEqual(summary(out)["HpcUser"]["changed"], 0)
        self.assertIn(f"Primary group {s._id('missing')} not found for user dave_c", err)

    def test_primary_group_moves_between_groups(self):
        s = baseline()
        s.users["dave"]["primary_group"] = "g1"
        self.run_import(s)
        self.assertEqual(HpcUser.objects.get(username="dave_c").primary_group_gid, 1001)

    def test_primary_group_set_and_cleared(self):
        s = baseline()
        s.users["carol"]["primary_group"] = "g1"  # alumna joins a group
        s.users["bob"]["primary_group"] = None  # member becomes alumnus
        self.run_import(s)
        self.assertEqual(HpcUser.objects.get(username="carol_m").primary_group_gid, 1001)
        self.assertIsNone(HpcUser.objects.get(username="bob_c").primary_group_gid)

    def test_group_fields_owner_and_delegate_updated(self):
        HpcGroup.objects.filter(gid=1001).update(expiration="2099-12-31T00:00:00Z")
        events_before = HpcGroup.objects.get(gid=1001).events.count()
        s = baseline()
        s.groups["g1"].update(
            owner="bob",
            delegate=None,
            description="new",
            status="EXPIRED",
            name="renamed",
            folders={"tier1_work": "/new/group"},
            resources_requested={"tier1_work": 20},
            resources_used={"tier1_work": 4},
        )
        out, _ = self.run_import(s)

        self.assertEqual(summary(out)["HpcGroup"]["changed"], 1)
        g1 = HpcGroup.objects.get(gid=1001)
        self.assertEqual(g1.owner.username, "bob_c")
        self.assertIsNone(g1.delegate)
        self.assertEqual((g1.description, g1.status, g1.name), ("new", "EXPIRED", "renamed"))
        self.assertEqual(g1.folders, {"tier1_work": "/new/group"})
        self.assertEqual(g1.resources_requested, {"tier1_work": 20})
        self.assertEqual(g1.resources_used, {"tier1_work": 4})
        self.assertEqual(g1.expiration, parse_datetime("2099-12-31T00:00:00Z"))
        self.assertGreater(g1.events.count(), events_before)

    def test_group_delegate_added(self):
        s = baseline()
        s.groups["g2"]["delegate"] = "carol"
        self.run_import(s)
        self.assertEqual(HpcGroup.objects.get(gid=1002).delegate.username, "carol_m")

    def test_project_members_delegate_group_and_fields_updated(self):
        HpcProject.objects.filter(name="proj1").update(expiration="2099-12-31T00:00:00Z")
        events_before = HpcProject.objects.get(name="proj1").events.count()
        s = baseline()
        s.projects["p1"].update(
            members=["bob", "carol"],
            delegate=None,
            group="g2",
            status="EXPIRED",
            gid=2999,
            folders={"tier1_work": "/new/project"},
            resources_requested={"tier1_work": 12},
            resources_used={"tier1_work": 3},
            expiration="2001-01-01T00:00:00+00:00",
        )
        out, _ = self.run_import(s)

        self.assertEqual(summary(out)["HpcProject"]["changed"], 1)
        p1 = HpcProject.objects.get(name="proj1")
        self.assertEqual({m.username for m in p1.members.all()}, {"bob_c", "carol_m"})
        self.assertIsNone(p1.delegate)
        self.assertEqual((p1.group.gid, p1.status), (1002, "EXPIRED"))
        self.assertEqual(p1.gid, 2999)
        self.assertEqual(p1.folders, {"tier1_work": "/new/project"})
        self.assertEqual(p1.resources_requested, {"tier1_work": 12})
        self.assertEqual(p1.resources_used, {"tier1_work": 3})
        self.assertEqual(p1.expiration, parse_datetime("2099-12-31T00:00:00Z"))
        self.assertGreater(p1.events.count(), events_before)

    def test_project_with_only_membership_change_is_detected(self):
        s = baseline()
        s.projects["p1"]["members"] = ["alice"]
        out, _ = self.run_import(s)
        self.assertEqual(summary(out)["HpcProject"]["changed"], 1)
        members = HpcProject.objects.get(name="proj1").members.all()
        self.assertEqual([m.username for m in members], ["alice_c"])

    def test_project_members_can_be_cleared(self):
        s = baseline()
        s.projects["p1"]["members"] = []
        out, _ = self.run_import(s)
        self.assertEqual(summary(out)["HpcProject"]["changed"], 1)
        self.assertFalse(HpcProject.objects.get(name="proj1").members.exists())

    def test_delegates_can_be_replaced_and_project_delegate_added(self):
        s = baseline()
        s.groups["g1"]["delegate"] = "carol"
        for delegate in ("carol", None, "alice"):
            with self.subTest(delegate=delegate):
                s.projects["p1"]["delegate"] = delegate
                self.run_import(s)
                self.assertEqual(HpcGroup.objects.get(gid=1001).delegate.username, "carol_m")
                project_delegate = HpcProject.objects.get(name="proj1").delegate
                self.assertEqual(
                    project_delegate.username if project_delegate else None,
                    s.users[delegate]["username"] if delegate else None,
                )

    def test_expiration_only_changes_are_ignored(self):
        s = baseline()
        for collection in (s.users, s.groups, s.projects):
            for data in collection.values():
                data["expiration"] = "2001-01-01T00:00:00+00:00"
        before = self.db_snapshot()
        out, _ = self.run_import(s, force=True)
        self.assertEqual(self.db_snapshot(), before)
        for counts in summary(out).values():
            self.assertEqual(counts["changed"], 0)

    def test_new_objects_added_next_to_existing_ones(self):
        s = baseline()
        s.user("erin", "erin_m", primary_group="g3")
        s.group("g3", gid=1003, owner="erin", delegate="alice")
        s.project("p2", "proj2", gid=2002, group="g3", members=["erin", "alice"])
        out, _ = self.run_import(s)

        counts = summary(out)
        self.assertEqual([counts[k]["added"] for k in ("User", "HpcUser", "HpcGroup")], [1] * 3)
        self.assertEqual(counts["HpcProject"]["added"], 1)
        erin = HpcUser.objects.get(username="erin_m")
        self.assertEqual(erin.primary_group_gid, 1003)
        self.assertEqual(HpcGroup.objects.get(gid=1003).owner, erin)
        self.assertEqual(HpcGroup.objects.get(gid=1003).delegate.username, "alice_c")
        self.assertEqual(HpcProject.objects.get(name="proj2").members.count(), 2)

    def test_existing_objects_can_reference_new_users_and_groups(self):
        s = baseline()
        s.user("erin", "erin_m", primary_group="g3")
        s.group("g3", gid=1003, owner="erin")
        s.groups["g1"].update(owner="erin", delegate="erin")
        s.users["dave"]["primary_group"] = "g3"
        s.projects["p1"].update(group="g3", delegate="erin", members=["erin"])
        self.run_import(s)
        erin = HpcUser.objects.get(username="erin_m")
        g1 = HpcGroup.objects.get(gid=1001)
        p1 = HpcProject.objects.get(name="proj1")
        self.assertEqual((g1.owner, g1.delegate, p1.delegate), (erin, erin, erin))
        self.assertEqual(p1.group.gid, 1003)
        self.assertEqual(list(p1.members.all()), [erin])
        self.assertEqual(HpcUser.objects.get(username="dave_c").primary_group_gid, 1003)


class TestRemovals(ImportCommandTestBase):
    def setUp(self):
        super().setUp()
        self.run_import(baseline())

    def test_removed_project_is_marked_deleted(self):
        """Removal is a soft delete: the row stays, with status DELETED."""
        s = baseline()
        del s.projects["p1"]
        out, _ = self.run_import(s)
        self.assertEqual(summary(out)["HpcProject"]["removed"], 1)
        self.assertEqual(HpcProject.objects.count(), 1)
        self.assertEqual(HpcProject.objects.get(name="proj1").status, OBJECT_STATUS_DELETED)
        self.assertFalse(HpcProject.objects.filter(status=OBJECT_STATUS_ACTIVE).exists())
        # the group is untouched
        self.assertEqual(HpcGroup.objects.count(), 2)
        self.assertEqual(HpcGroup.objects.filter(status=OBJECT_STATUS_ACTIVE).count(), 2)

    def test_changed_key_means_delete_and_recreate(self):
        """A new gid / project name is a different object, old one is marked deleted."""
        old_pk = HpcGroup.objects.get(gid=1002).pk
        s = baseline("salt")
        s.groups["g2"]["gid"] = 1999
        s.groups["g2"]["name"] = "grp-g2-new"  # name is unique in the db
        s.projects["p1"]["name"] = "proj1-renamed"
        self.run_import(s)
        self.assertTrue(HpcGroup.objects.filter(gid=1002, status=OBJECT_STATUS_DELETED).exists())
        self.assertFalse(HpcGroup.objects.filter(gid=1002, status=OBJECT_STATUS_ACTIVE).exists())
        self.assertNotEqual(HpcGroup.objects.get(gid=1999).pk, old_pk)
        self.assertEqual(HpcGroup.objects.get(gid=1999).status, OBJECT_STATUS_ACTIVE)
        self.assertEqual(HpcProject.objects.get(name="proj1").status, OBJECT_STATUS_DELETED)
        self.assertEqual(HpcProject.objects.get(name="proj1-renamed").status, OBJECT_STATUS_ACTIVE)
        self.assertEqual(HpcUser.objects.get(username="dave_c").primary_group_gid, 1999)

    def test_removed_group_keeps_users_that_moved_elsewhere(self):
        """dave leaves g2, which disappears; dave himself must survive."""
        s = baseline()
        s.users["dave"]["primary_group"] = "g1"
        del s.groups["g2"]
        self.run_import(s)
        self.assertEqual(HpcGroup.objects.get(gid=1002).status, OBJECT_STATUS_DELETED)
        self.assertEqual(HpcUser.objects.get(username="dave_c").primary_group_gid, 1001)

    def test_removed_hpc_user_is_soft_deleted_and_account_is_anonymized(self):
        s = baseline()
        del s.users["carol"]
        carol_pk = User.objects.get(username="carol@MDC-BERLIN").pk
        with mock.patch.object(
            COMMAND_MODULE, "anonymize_user", wraps=COMMAND_MODULE.anonymize_user
        ) as anonymize:
            out, _ = self.run_import(s)
        anonymize.assert_called_once()
        self.assertEqual(anonymize.call_args.args[0].pk, carol_pk)
        self.assertEqual(summary(out)["User"]["removed"], 1)
        self.assertEqual(summary(out)["HpcUser"]["removed"], 1)
        self.assertEqual(HpcUser.objects.get(username="carol_m").status, OBJECT_STATUS_DELETED)

    def test_removed_group_does_not_take_users_down_when_json_primary_group_is_a_project(self):
        """Moving a user to a project's GID survives deletion of their old group."""
        s = baseline()
        s.users["dave"]["primary_group"] = "p1"
        del s.groups["g2"]
        self.run_import(s)
        dave = HpcUser.objects.get(username="dave_c")
        self.assertEqual(dave.status, OBJECT_STATUS_ACTIVE)
        self.assertEqual(dave.primary_group_gid, 2001)
        self.assertEqual(HpcGroup.objects.get(gid=1002).status, OBJECT_STATUS_DELETED)

    def test_replacing_a_group_owner_who_is_removed_keeps_group_and_projects(self):
        """Regression: HpcGroup.owner is on_delete=CASCADE.

        alice (owner of g1) disappears and bob takes over g1.  g1 and its
        project p1 stay in the json, so they must survive in the database.
        """
        s = baseline()
        del s.users["alice"]
        s.groups["g1"]["owner"] = "bob"
        s.projects["p1"]["members"] = ["bob"]
        self.run_import(s)
        self.assertEqual(HpcUser.objects.get(username="alice_c").status, OBJECT_STATUS_DELETED)
        self.assertEqual(HpcUser.objects.get(username="carol_m").status, OBJECT_STATUS_ACTIVE)
        self.assertEqual(HpcGroup.objects.get(gid=1001).owner.username, "bob_c")
        self.assertEqual(HpcGroup.objects.get(gid=1001).status, OBJECT_STATUS_ACTIVE)
        self.assertEqual(HpcProject.objects.get(name="proj1").status, OBJECT_STATUS_ACTIVE)

    def test_staff_inactive_and_non_hpc_accounts_are_not_anonymized(self):
        User.objects.filter(username="carol@MDC-BERLIN").update(is_staff=True)
        User.objects.filter(username="dave@CHARITE").update(is_active=False)
        standalone = User.objects.create(username="standalone@CHARITE")
        s = baseline()
        del s.users["carol"]
        del s.users["dave"]
        del s.groups["g2"]
        with mock.patch.object(COMMAND_MODULE, "anonymize_user") as anonymize:
            out, _ = self.run_import(s)
        anonymize.assert_not_called()
        self.assertEqual(summary(out)["User"]["removed"], 0)
        self.assertTrue(User.objects.filter(pk=standalone.pk).exists())
        self.assertEqual(HpcUser.objects.get(username="carol_m").status, OBJECT_STATUS_DELETED)
        self.assertEqual(HpcUser.objects.get(username="dave_c").status, OBJECT_STATUS_DELETED)

    def test_already_deleted_objects_are_not_removed_again(self):
        s = baseline()
        del s.projects["p1"]
        del s.groups["g2"]
        del s.users["dave"]
        self.run_import(s)
        before = self.db_snapshot()
        with mock.patch.object(COMMAND_MODULE, "anonymize_user") as anonymize:
            out, _ = self.run_import(s, force=True)
        anonymize.assert_not_called()
        self.assertEqual(self.db_snapshot(), before)
        counts = summary(out)
        for model in ("HpcUser", "HpcGroup", "HpcProject"):
            self.assertEqual(counts[model]["removed"], 0)
        self.assertEqual(counts["HpcUser"]["initial"], 3)
        self.assertEqual(counts["HpcGroup"]["initial"], 1)
        self.assertEqual(counts["HpcProject"]["initial"], 0)

    def test_deleted_group_and_project_are_reused_when_they_reappear(self):
        group = HpcGroup.objects.get(gid=1002)
        project = HpcProject.objects.get(name="proj1")
        s = baseline()
        s.users["dave"]["primary_group"] = None
        del s.groups["g2"]
        del s.projects["p1"]
        self.run_import(s)
        out, _ = self.run_import(baseline("fresh-export"))
        for model, obj in ((HpcGroup, group), (HpcProject, project)):
            obj.refresh_from_db()
            self.assertEqual(obj.status, OBJECT_STATUS_ACTIVE)
            self.assertEqual(summary(out)[model.__name__]["added"], 0)
            self.assertEqual(summary(out)[model.__name__]["changed"], 1)
        self.assertEqual(HpcProject.objects.get(name="proj1").members.count(), 2)


class TestCommandBehaviour(ImportCommandTestBase):
    def test_confirmation_declined_leaves_database_untouched(self):
        before = self.db_snapshot()
        out, _ = self.run_import(baseline(), answer="n")
        self.assertEqual(self.db_snapshot(), before)
        self.assertIn("The database was not changed", out)
        self.assertFalse(HpcUser.objects.exists())
        self.assertFalse(User.objects.filter(username="alice@CHARITE").exists())

    def test_confirmation_accepted_applies_changes(self):
        for index, answer in enumerate(("", "y", "Y")):
            with self.subTest(answer=answer):
                s = baseline()
                s.users["alice"]["email"] = f"alice{index}@example.com"
                self.run_import(s, answer=answer)
                self.assertEqual(HpcUser.objects.count(), 4)
                self.assertEqual(
                    User.objects.get(username="alice@CHARITE").email,
                    f"alice{index}@example.com",
                )

    def test_report_is_printed_before_writing(self):
        out = StringIO()
        with mock.patch.object(
            User, "save", autospec=True, side_effect=RuntimeError("stop before saving")
        ):
            with self.assertRaisesMessage(RuntimeError, "stop before saving"):
                self.run_import(baseline(), stdout=out)
        out = out.getvalue()
        counts = summary(out)
        self.assertEqual(counts["HpcUser"], {"initial": 0, "added": 4, "removed": 0, "changed": 0})
        self.assertNotIn("Done.", out)

    def test_missing_worker_user_fails_cleanly(self):
        User.objects.filter(username="hpc-worker").delete()
        with self.assertRaises(User.DoesNotExist):
            self.run_import(baseline())
        self.assertFalse(HpcUser.objects.exists())

    def test_unmappable_username_aborts_without_changes(self):
        for bad in ("nosuffix", "too_many_parts_c", "alice_x"):
            with self.subTest(username=bad):
                s = baseline()
                s.users["alice"]["username"] = bad
                with self.assertRaises((KeyError, ValueError)):
                    self.run_import(s)
                self.assertFalse(HpcUser.objects.exists())
                self.assertFalse(User.objects.filter(username__startswith="bob").exists())

    def test_failure_while_writing_rolls_back_and_reraises_original_error(self):
        self.run_import(baseline())
        before = self.db_snapshot()
        s = baseline()
        s.users["erin"] = dict(s.users["alice"], username="erin_c", uid=7777, primary_group=None)
        s.users["bob"]["email"] = "changed@example.com"
        del s.users["carol"]  # exercise anonymization and soft deletion before failure
        s.projects["p1"]["status"] = "EXPIRED"  # forces the project-update step
        error = RuntimeError("boom")
        err = StringIO()
        with mock.patch.object(HpcProject, "save", side_effect=error):
            with self.assertRaisesMessage(RuntimeError, "boom"):
                try:
                    self.run_import(s, stderr=err)
                except RuntimeError as exc:
                    self.assertIs(exc, error)
                    raise
        self.assertEqual(self.db_snapshot(), before)  # nothing from the failed run persisted
        self.assertIn("Transaction will be aborted due to RuntimeError: boom", err.getvalue())

    def test_failure_setting_project_members_rolls_back_field_changes(self):
        self.run_import(baseline())
        before = self.db_snapshot()
        s = baseline()
        s.users["bob"]["email"] = "changed@example.com"
        s.projects["p1"].update(status="EXPIRED", members=["carol"])
        manager_type = type(HpcProject.objects.get(name="proj1").members)
        with mock.patch.object(manager_type, "set", side_effect=RuntimeError("members failed")):
            with self.assertRaisesMessage(RuntimeError, "members failed"):
                self.run_import(s)
        self.assertEqual(self.db_snapshot(), before)


class TestForceGuardrail(ImportCommandTestBase):
    def seeded_state(self, size):
        """Seed N accounts: one account-only change contributes 100/N percent."""
        s = baseline()
        for index in range(4, size):
            s.user(f"extra{index}", f"extra{index}_c")
        self.run_import(s)
        return s

    def test_force_allows_initial_import_with_no_existing_objects(self):
        out, _ = self.run_import(baseline(), force=True)
        self.assertEqual(HpcUser.objects.count(), 4)
        self.assertIn("0% of the database has changed.", out)
        self.assertIn("Done.", out)

    def test_force_allows_changes_below_threshold(self):
        s = self.seeded_state(6)
        s.users["bob"]["email"] = "new@example.com"
        out, err = self.run_import(s, force=True)
        self.assertEqual(User.objects.get(username="bob@CHARITE").email, "new@example.com")
        self.assertIn("17% of the database has changed.", out)
        self.assertEqual(err, "")

    def test_force_rejects_changes_at_and_above_threshold(self):
        s = self.seeded_state(4)
        for size, percent in ((4, 25), (5, 20)):
            with self.subTest(percent=percent):
                if size == 5:
                    s.user("extra4", "extra4_c")
                    self.run_import(s)
                s.users["bob"]["email"] = f"changed{size}@example.com"
                before = self.db_snapshot()
                out, err = StringIO(), StringIO()
                with self.assertRaisesMessage(RuntimeError, "Too many changes"):
                    self.run_import(s, force=True, stdout=out, stderr=err)
                self.assertEqual(self.db_snapshot(), before)
                self.assertIn(f"{percent}% of the database has changed.", out.getvalue())
                self.assertIn("--force cannot be used", err.getvalue())
                self.assertNotIn("Applying changes", out.getvalue())

    def test_force_sums_percentages_across_model_types(self):
        s = self.seeded_state(6)
        s.users["bob"].update(email="new@example.com", uid=9999)
        before = self.db_snapshot()
        out = StringIO()
        with self.assertRaisesMessage(RuntimeError, "Too many changes"):
            self.run_import(s, force=True, stdout=out)
        # Each of User and HpcUser changes by 1/6; their percentages are summed.
        self.assertIn("33% of the database has changed.", out.getvalue())
        self.assertEqual(self.db_snapshot(), before)

    def test_force_guardrail_counts_removals_and_additions(self):
        self.seeded_state(6)
        for operation in ("add", "remove"):
            with self.subTest(operation=operation):
                candidate = baseline()
                candidate.user("extra4", "extra4_c").user("extra5", "extra5_c")
                if operation == "add":
                    candidate.user("erin", "erin_m")
                else:
                    del candidate.users["carol"]
                before = self.db_snapshot()
                out = StringIO()
                with self.assertRaisesMessage(RuntimeError, "Too many changes"):
                    self.run_import(candidate, force=True, stdout=out)
                self.assertIn("33% of the database has changed.", out.getvalue())
                self.assertEqual(self.db_snapshot(), before)
