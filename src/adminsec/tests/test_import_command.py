"""Tests for the ``import`` management command"""

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

from usersec.models import HpcGroup, HpcProject, HpcUser

User = get_user_model()

COMMAND = "import"
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
        pg_keys = {**{k: k for k in self.groups}, **{k: k for k in self.projects}}
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
        assert not (set(pg_keys) - set(self.groups) - set(self.projects))
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

    def run_import(self, state, *args, force=True):
        """Run the command on ``state`` (a State or dict); return (stdout, stderr)."""
        doc = state.to_dict() if isinstance(state, State) else state
        out, err = StringIO(), StringIO()
        with tempfile.NamedTemporaryFile("w", suffix=".json") as fp:
            json.dump(doc, fp)
            fp.flush()
            extra = ["--force"] if force else []
            call_command(COMMAND, fp.name, *extra, *args, stdout=out, stderr=err)
        return out.getvalue(), err.getvalue()

    def db_snapshot(self):
        return (
            sorted(User.objects.values_list("username", "email")),
            sorted(HpcUser.objects.values_list("pk", "username", "current_version")),
            sorted(HpcGroup.objects.values_list("pk", "gid", "current_version")),
            sorted(HpcProject.objects.values_list("pk", "name", "current_version")),
        )


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

        # Circular references: user -> primary group -> owner/delegate -> user
        self.assertEqual(alice.primary_group, g1)
        self.assertEqual(bob.primary_group, g1)
        self.assertIsNone(carol.primary_group)
        self.assertEqual(g1.owner, alice)
        self.assertEqual(g1.delegate, bob)
        self.assertIsNone(HpcGroup.objects.get(gid=1002).delegate)
        self.assertEqual(g1.creator, self.worker)

        # Project
        p1 = HpcProject.objects.get(name="proj1")
        self.assertEqual(p1.group, g1)
        self.assertEqual(p1.delegate, bob)
        self.assertEqual({m.username for m in p1.members.all()}, {"alice_c", "bob_c"})

    def test_creates_version_history(self):
        self.run_import(baseline())
        for obj in (HpcUser.objects.get(username="alice_c"), HpcGroup.objects.get(gid=1001)):
            self.assertEqual(obj.current_version, 1)
            self.assertEqual(obj.version_history.count(), 1)
        self.assertEqual(HpcProject.objects.get(name="proj1").version_history.count(), 1)

    def test_names_are_stripped_and_empty_values_tolerated(self):
        s = baseline()
        s.users["carol"].update(
            first_name="  Carol ", last_name=None, full_name=" Carol X ", display_name=None
        )
        self.run_import(s)
        u = User.objects.get(username="carol@MDC-BERLIN")
        self.assertEqual((u.first_name, u.last_name), ("Carol", ""))
        self.assertEqual((u.name, u.display_name), ("Carol X", ""))

    def test_primary_group_pointing_to_project_is_reported_not_assigned(self):
        s = baseline()
        s.users["carol"]["primary_group"] = "p1"
        _, err = self.run_import(s)
        self.assertIsNone(HpcUser.objects.get(username="carol_m").primary_group)
        self.assertIn("Cannot assign project", err)
        self.assertIn("carol_m", err)


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

        self.assertEqual(self.db_snapshot(), before)  # same pks, same versions
        self.assertEqual(set(HpcUser.objects.values_list("uuid", flat=True)), uuids_before)
        self.assertEqual(summary(out)["HpcGroup"]["added"], 0)
        # relationships survive
        self.assertEqual(HpcGroup.objects.get(gid=1001).owner.username, "alice_c")
        self.assertEqual(HpcProject.objects.get(name="proj1").members.count(), 2)


class TestUpdates(ImportCommandTestBase):
    def setUp(self):
        super().setUp()
        self.run_import(baseline())

    def test_hpc_user_fields_updated_but_expiration_and_consent_preserved(self):
        HpcUser.objects.filter(username="bob_c").update(expiration="2099-12-31T00:00:00Z")
        User.objects.filter(username="bob@CHARITE").update(consented_to_terms=True)
        s = baseline()
        s.users["bob"].update(
            uid=9999,
            status="EXPIRED",
            login_shell="/usr/bin/zsh",
            home_directory="/new/home",
            resources_requested={"tier1_home": 7},
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
        self.assertEqual(bob.expiration, parse_datetime("2099-12-31T00:00:00Z"))
        self.assertEqual(bob.current_version, 2)
        self.assertEqual(bob.version_history.count(), 2)
        self.assertTrue(User.objects.get(username="bob@CHARITE").consented_to_terms)

    def test_django_user_fields_updated(self):
        s = baseline()
        s.users["alice"].update(email="new@example.com", phone_number="123", full_name="A. T.")
        out, _ = self.run_import(s)
        self.assertEqual(summary(out)["User"]["changed"], 1)
        u = User.objects.get(username="alice@CHARITE")
        self.assertEqual((u.email, u.phone, u.name), ("new@example.com", "123", "A. T."))

    def test_primary_group_moves_between_groups(self):
        s = baseline()
        s.users["dave"]["primary_group"] = "g1"
        self.run_import(s)
        self.assertEqual(HpcUser.objects.get(username="dave_c").primary_group.gid, 1001)

    def test_primary_group_set_and_cleared(self):
        s = baseline()
        s.users["carol"]["primary_group"] = "g1"  # alumna joins a group
        s.users["bob"]["primary_group"] = None  # member becomes alumnus
        self.run_import(s)
        self.assertEqual(HpcUser.objects.get(username="carol_m").primary_group.gid, 1001)
        self.assertIsNone(HpcUser.objects.get(username="bob_c").primary_group)

    def test_group_fields_owner_and_delegate_updated(self):
        HpcGroup.objects.filter(gid=1001).update(expiration="2099-12-31T00:00:00Z")
        s = baseline()
        s.groups["g1"].update(
            owner="bob", delegate=None, description="new", status="EXPIRED", name="renamed"
        )
        out, _ = self.run_import(s)

        self.assertEqual(summary(out)["HpcGroup"]["changed"], 1)
        g1 = HpcGroup.objects.get(gid=1001)
        self.assertEqual(g1.owner.username, "bob_c")
        self.assertIsNone(g1.delegate)
        self.assertEqual((g1.description, g1.status, g1.name), ("new", "EXPIRED", "renamed"))
        self.assertEqual(g1.expiration, parse_datetime("2099-12-31T00:00:00Z"))
        self.assertEqual(g1.current_version, 2)

    def test_group_delegate_added(self):
        s = baseline()
        s.groups["g2"]["delegate"] = "carol"
        self.run_import(s)
        self.assertEqual(HpcGroup.objects.get(gid=1002).delegate.username, "carol_m")

    def test_project_members_delegate_group_and_fields_updated(self):
        s = baseline()
        s.projects["p1"].update(
            members=["bob", "carol"], delegate=None, group="g2", status="EXPIRED"
        )
        out, _ = self.run_import(s)

        self.assertEqual(summary(out)["HpcProject"]["changed"], 1)
        p1 = HpcProject.objects.get(name="proj1")
        self.assertEqual({m.username for m in p1.members.all()}, {"bob_c", "carol_m"})
        self.assertIsNone(p1.delegate)
        self.assertEqual((p1.group.gid, p1.status), (1002, "EXPIRED"))
        self.assertEqual(p1.current_version, 2)

    def test_project_with_only_membership_change_is_detected(self):
        s = baseline()
        s.projects["p1"]["members"] = ["alice"]
        out, _ = self.run_import(s)
        self.assertEqual(summary(out)["HpcProject"]["changed"], 1)
        members = HpcProject.objects.get(name="proj1").members.all()
        self.assertEqual([m.username for m in members], ["alice_c"])

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
        self.assertEqual(erin.primary_group.owner, erin)
        self.assertEqual(HpcGroup.objects.get(gid=1003).delegate.username, "alice_c")
        self.assertEqual(HpcProject.objects.get(name="proj2").members.count(), 2)


class TestRemovals(ImportCommandTestBase):
    def setUp(self):
        super().setUp()
        self.run_import(baseline())

    def test_removed_project_is_deleted(self):
        s = baseline()
        del s.projects["p1"]
        out, _ = self.run_import(s)
        self.assertEqual(summary(out)["HpcProject"]["removed"], 1)
        self.assertFalse(HpcProject.objects.exists())
        self.assertEqual(HpcGroup.objects.count(), 2)

    def test_changed_key_means_delete_and_recreate(self):
        """A new gid / project name is a different object, old one is dropped."""
        old_pk = HpcGroup.objects.get(gid=1002).pk
        s = baseline("salt")
        s.groups["g2"]["gid"] = 1999
        s.groups["g2"]["name"] = "grp-g2-new"  # name is unique in the db
        s.projects["p1"]["name"] = "proj1-renamed"
        self.run_import(s)
        self.assertFalse(HpcGroup.objects.filter(gid=1002).exists())
        self.assertNotEqual(HpcGroup.objects.get(gid=1999).pk, old_pk)
        self.assertEqual(HpcProject.objects.get().name, "proj1-renamed")
        self.assertEqual(HpcUser.objects.get(username="dave_c").primary_group.gid, 1999)

    def test_removed_group_keeps_users_that_moved_elsewhere(self):
        """dave leaves g2, which disappears; dave himself must survive."""
        s = baseline()
        s.users["dave"]["primary_group"] = "g1"
        del s.groups["g2"]
        self.run_import(s)
        self.assertFalse(HpcGroup.objects.filter(gid=1002).exists())
        self.assertEqual(HpcUser.objects.get(username="dave_c").primary_group.gid, 1001)

    def test_removed_hpc_user_is_deleted_but_django_user_is_kept(self):
        s = baseline()
        del s.users["carol"]
        out, _ = self.run_import(s)
        self.assertEqual(summary(out)["HpcUser"]["removed"], 1)
        self.assertFalse(HpcUser.objects.filter(username="carol_m").exists())
        self.assertTrue(User.objects.filter(username="carol@MDC-BERLIN").exists())

    def test_removed_group_does_not_take_users_down_when_json_primary_group_is_a_project(self):
        """Regression: HpcUser.primary_group is on_delete=CASCADE.

        If the json says a user's primary group is a *project* (which cannot
        be represented), the importer keeps the old FK; deleting the old group
        then silently cascades to the user.
        """
        s = baseline()
        s.users["dave"]["primary_group"] = "p1"
        del s.groups["g2"]
        self.run_import(s)
        self.assertTrue(HpcUser.objects.filter(username="dave_c").exists())

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
        self.assertFalse(HpcUser.objects.filter(username="alice_c").exists())
        self.assertEqual(HpcGroup.objects.get(gid=1001).owner.username, "bob_c")
        self.assertTrue(HpcProject.objects.filter(name="proj1").exists())


class TestCommandBehaviour(ImportCommandTestBase):
    def test_confirmation_declined_leaves_database_untouched(self):
        with mock.patch("builtins.input", return_value="n"):
            out, _ = self.run_import(baseline(), force=False)
        self.assertFalse(HpcUser.objects.exists())
        self.assertFalse(User.objects.filter(username="alice@CHARITE").exists())

    def test_confirmation_accepted_applies_changes(self):
        for answer in ("", "y"):
            with self.subTest(answer=answer), mock.patch("builtins.input", return_value=answer):
                HpcProject.objects.all().delete()
                HpcGroup.objects.all().delete()
                HpcUser.objects.all().delete()
                self.run_import(baseline(), force=False)
                self.assertEqual(HpcUser.objects.count(), 4)

    def test_report_is_printed_before_writing(self):
        out, _ = self.run_import(baseline())
        counts = summary(out)
        self.assertEqual(counts["HpcUser"], {"initial": 0, "added": 4, "removed": 0, "changed": 0})
        self.assertIn("Done.", out)

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
        s.projects["p1"]["status"] = "EXPIRED"  # forces the project-update step
        with mock.patch.object(HpcProject, "update_with_version", side_effect=RuntimeError("boom")):
            with self.assertRaisesMessage(RuntimeError, "boom"):
                self.run_import(s)
        self.assertEqual(self.db_snapshot(), before)  # nothing from the failed run persisted
