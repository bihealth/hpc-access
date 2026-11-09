"""Database tests for the ``import`` management command.

The command never deletes or deactivates anything: records that are absent from
the json file are only *reported* as "missing" (without blocking writes).
The tests below pin that behaviour. Imports are dry-run by default; the helper
passes --write unless write=False.

Run with ``./manage.py test -v2 adminsec.tests.test_import_command``. Requires
the project's normal test database, including django-pghistory triggers.
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
from django.core.management.base import CommandError
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

    def run_import(
        self,
        state,
        *args,
        write=True,
        stdout=None,
        stderr=None,
        before_execute=None,
        verbosity=1,
    ):
        """Most fixtures explicitly write; pass write=False to test the CLI default.

        before_execute simulates an intervening edit in the same transaction. It
        tests stale-column protection, not cross-connection locking.
        """
        doc = state.to_dict() if isinstance(state, State) else state
        out = stdout if stdout is not None else StringIO()
        err = stderr if stderr is not None else StringIO()
        execute = COMMAND_MODULE.Command._execute_plan

        def wrapped_execute(command, objects, updates):
            if before_execute:
                before_execute()
            return execute(command, objects, updates)

        with tempfile.NamedTemporaryFile("w", suffix=".json") as fp:
            json.dump(doc, fp)
            fp.flush()
            extra = ["--write"] if write else []
            with (
                mock.patch(
                    "builtins.input", side_effect=AssertionError("Unexpected prompt")
                ) as prompt,
                mock.patch.object(COMMAND_MODULE.Command, "_execute_plan", wrapped_execute),
            ):
                call_command(
                    COMMAND,
                    fp.name,
                    *extra,
                    *args,
                    stdout=out,
                    stderr=err,
                    verbosity=verbosity,
                )
                prompt.assert_not_called()
        return out.getvalue(), err.getvalue()

    def read_state(self, state):
        """Exercise normalization directly without database constraints masking it."""
        err = StringIO()
        command = COMMAND_MODULE.Command(stderr=err)
        with tempfile.NamedTemporaryFile("w", suffix=".json") as fp:
            json.dump(state.to_dict(), fp)
            fp.flush()
            result = command._read_hpcaccess_state(fp.name)
        return result, err.getvalue()

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

        # Primary groups are foreign keys to HpcGroup, resolved by group name.
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

    def test_user_with_project_as_primary_group_is_skipped(self):
        s = baseline()
        s.users["carol"]["primary_group"] = "p1"
        _, err = self.run_import(s)
        self.assertFalse(HpcUser.objects.filter(username="carol_m").exists())
        self.assertFalse(User.objects.filter(username="carol@MDC-BERLIN").exists())
        self.assertIn("is a project. This user will be skipped.", err)


class TestIdempotencyAndKeys(ImportCommandTestBase):
    def test_reimport_of_same_file_changes_nothing(self):
        self.run_import(baseline())
        before = self.db_snapshot()
        out, err = self.run_import(baseline())
        self.assertEqual(self.db_snapshot(), before)
        for name, counts in summary(out).items():
            self.assertEqual(
                (counts["added"], counts["missing"], counts["changed"]), (0, 0, 0), name
            )
        self.assertEqual(err, "")

    def test_json_uuids_are_irrelevant_for_existing_objects(self):
        """Objects are matched by username / group name / project name, never by json UUIDs."""
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
        out, _ = self.run_import(s)
        self.assertEqual(summary(out)["HpcProject"]["changed"], 0)

    def test_existing_account_without_hpc_user_is_reused(self):
        """Someone logged in before their LDAP account existed: the User is adopted."""
        account = User.objects.create(
            username="alice@CHARITE", email="old@example.com", consented_to_terms=True
        )
        out, _ = self.run_import(baseline())

        self.assertEqual(User.objects.filter(username="alice@CHARITE").count(), 1)
        alice = HpcUser.objects.get(username="alice_c")
        self.assertEqual(alice.user_id, account.pk)
        account.refresh_from_db()
        self.assertTrue(account.consented_to_terms)  # not reset by the import
        self.assertEqual(account.email, "alice@example.com")  # but synced from the file
        counts = summary(out)["User"]
        # it had no HpcUser, so it is neither an initial object nor a new one
        self.assertEqual(
            (counts["initial"], counts["added"], counts["changed"], counts["missing"]),
            (0, 3, 1, 0),
        )

    def test_existing_account_without_hpc_user_is_reused_in_dry_run(self):
        User.objects.create(username="alice@CHARITE", email="old@example.com")
        before = self.db_snapshot()
        out, _ = self.run_import(baseline(), write=False)
        self.assertEqual(self.db_snapshot(), before)
        self.assertEqual(summary(out)["User"]["added"], 3)
        self.assertEqual(summary(out)["HpcUser"]["added"], 4)

    def test_existing_account_without_hpc_user_stays_inactive(self):
        """The import adopts the account but never changes who may log in."""
        User.objects.create(username="alice@CHARITE", is_active=False)
        self.run_import(baseline())
        self.assertFalse(User.objects.get(username="alice@CHARITE").is_active)


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
        self.assertEqual(bob.resources_used, {"tier1_home": 0})
        self.assertEqual(bob.expiration, parse_datetime("2099-12-31T00:00:00Z"))
        self.assertGreater(bob.events.count(), events_before)
        self.assertTrue(User.objects.get(username="bob@CHARITE").consented_to_terms)

    def test_intervening_changes_to_unmanaged_fields_survive_the_import(self):
        """Only the changed columns are written, so values the file cannot provide (consent,
        expiration) that were modified after the plan was built are not reverted."""
        s = baseline()
        s.users["bob"].update(email="new@example.com", uid=9999)
        s.groups["g1"]["description"] = "new"
        s.projects["p1"]["status"] = "EXPIRED"

        def concurrent_edit():
            User.objects.filter(username="bob@CHARITE").update(consented_to_terms=True)
            HpcUser.objects.filter(username="bob_c").update(expiration="2099-12-31T00:00:00Z")
            HpcGroup.objects.filter(name="grp-g1").update(expiration="2099-12-31T00:00:00Z")
            HpcProject.objects.filter(name="proj1").update(expiration="2099-12-31T00:00:00Z")

        self.run_import(s, before_execute=concurrent_edit)

        expiration = parse_datetime("2099-12-31T00:00:00Z")
        user = User.objects.get(username="bob@CHARITE")
        self.assertEqual(user.email, "new@example.com")  # the import did apply its changes
        self.assertTrue(user.consented_to_terms)
        hpc_user = HpcUser.objects.get(username="bob_c")
        self.assertEqual(hpc_user.uid, 9999)
        self.assertEqual(hpc_user.expiration, expiration)
        group = HpcGroup.objects.get(name="grp-g1")
        self.assertEqual(group.description, "new")
        self.assertEqual(group.expiration, expiration)
        project = HpcProject.objects.get(name="proj1")
        self.assertEqual(project.status, "EXPIRED")
        self.assertEqual(project.expiration, expiration)

    def test_save_only_writes_changed_columns(self):
        s = baseline()
        s.users["bob"]["email"] = "new@example.com"
        s.groups["g1"]["description"] = "new"
        with (
            mock.patch.object(User, "save", autospec=True, side_effect=User.save) as user_save,
            mock.patch.object(HpcGroup, "save", autospec=True, side_effect=HpcGroup.save) as gsave,
        ):
            self.run_import(s)
        user_save.assert_called_once()
        self.assertEqual(user_save.call_args.kwargs["update_fields"], ["email"])
        gsave.assert_called_once()
        self.assertEqual(gsave.call_args.kwargs["update_fields"], ["description"])

    def test_membership_only_project_change_does_not_save_the_project(self):
        s = baseline()
        s.projects["p1"]["members"] = ["alice"]
        with mock.patch.object(HpcProject, "save", autospec=True) as project_save:
            self.run_import(s)
        project_save.assert_not_called()
        members = HpcProject.objects.get(name="proj1").members.all()
        self.assertEqual([m.username for m in members], ["alice_c"])

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
        self.assertIn('Warning: User "bob@CHARITE" is not active', err)

    def test_existing_user_with_project_primary_group_is_left_untouched(self):
        s = baseline()
        s.users["carol"].update(primary_group="p1", uid=9999)
        before = self.db_snapshot()
        out, err = self.run_import(s)
        self.assertEqual(self.db_snapshot(), before)
        self.assertEqual(summary(out)["HpcUser"]["missing"], 1)
        self.assertIn("This user will be skipped.", err)

    def test_missing_primary_group_reference_skips_user_without_changes(self):
        s = baseline()
        s.users["carol"].update(primary_group="missing", uid=9999)
        before = self.db_snapshot()
        _, err = self.run_import(s)
        self.assertEqual(self.db_snapshot(), before)
        self.assertIn("missing primary_group reference", err)

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
        HpcGroup.objects.filter(name="grp-g1").update(expiration="2099-12-31T00:00:00Z")
        events_before = HpcGroup.objects.get(name="grp-g1").events.count()
        s = baseline()
        s.groups["g1"].update(
            owner="bob",
            delegate=None,
            description="new",
            status="EXPIRED",
            gid=1999,
            folders={"tier1_work": "/new/group"},
            resources_requested={"tier1_work": 20},
            resources_used={"tier1_work": 4},
        )
        out, _ = self.run_import(s)

        self.assertEqual(summary(out)["HpcGroup"]["changed"], 1)
        g1 = HpcGroup.objects.get(name="grp-g1")
        self.assertEqual(g1.owner.username, "bob_c")
        self.assertIsNone(g1.delegate)
        self.assertEqual((g1.description, g1.status, g1.gid), ("new", "EXPIRED", 1999))
        self.assertEqual(g1.folders, {"tier1_work": "/new/group"})
        self.assertEqual(g1.resources_requested, {"tier1_work": 20})
        self.assertEqual(g1.resources_used, {"tier1_work": 1})
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
        self.assertEqual(p1.resources_used, {"tier1_work": 1})
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
        out, _ = self.run_import(s)
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
        self.assertEqual(erin.primary_group.gid, 1003)
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
        self.assertEqual(HpcUser.objects.get(username="dave_c").primary_group.gid, 1003)


class TestMissingRecords(ImportCommandTestBase):
    """Records absent from the file are reported, never modified."""

    def setUp(self):
        super().setUp()
        self.run_import(baseline())

    def test_missing_project_is_reported_and_left_untouched(self):
        s = baseline()
        del s.projects["p1"]
        before = self.db_snapshot()
        out, _ = self.run_import(s)
        self.assertEqual(summary(out)["HpcProject"]["missing"], 1)
        self.assertEqual(self.db_snapshot(), before)
        self.assertEqual(HpcProject.objects.get(name="proj1").status, OBJECT_STATUS_ACTIVE)
        self.assertEqual(HpcProject.objects.get(name="proj1").members.count(), 2)

    def test_changed_name_creates_a_new_object_and_reports_the_old_one_missing(self):
        """Groups and projects are keyed by name: a new name is a different object."""
        old_pk = HpcGroup.objects.get(name="grp-g2").pk
        s = baseline("salt")
        s.groups["g2"]["name"] = "grp-g2-new"
        s.groups["g2"]["gid"] = 1999  # gid is unique in the db
        s.projects["p1"]["name"] = "proj1-renamed"
        s.projects["p1"]["gid"] = 2101
        out, _ = self.run_import(s)
        counts = summary(out)
        self.assertEqual((counts["HpcGroup"]["added"], counts["HpcGroup"]["missing"]), (1, 1))
        self.assertEqual((counts["HpcProject"]["added"], counts["HpcProject"]["missing"]), (1, 1))
        self.assertEqual(HpcGroup.objects.get(name="grp-g2").pk, old_pk)
        self.assertEqual(HpcGroup.objects.get(name="grp-g2").status, OBJECT_STATUS_ACTIVE)
        self.assertNotEqual(HpcGroup.objects.get(name="grp-g2-new").pk, old_pk)
        self.assertEqual(HpcProject.objects.get(name="proj1").status, OBJECT_STATUS_ACTIVE)
        self.assertEqual(HpcProject.objects.get(name="proj1-renamed").status, OBJECT_STATUS_ACTIVE)
        self.assertEqual(HpcUser.objects.get(username="dave_c").primary_group.name, "grp-g2-new")

    def test_changed_gid_updates_the_existing_group_and_project(self):
        """A gid is a plain field: the objects keep their pk and are not reported missing."""
        group_pk = HpcGroup.objects.get(name="grp-g2").pk
        project_pk = HpcProject.objects.get(name="proj1").pk
        s = baseline()
        s.groups["g2"]["gid"] = 1999
        s.projects["p1"]["gid"] = 2101
        out, _ = self.run_import(s)
        counts = summary(out)
        for model in ("HpcGroup", "HpcProject"):
            self.assertEqual(
                (counts[model]["added"], counts[model]["missing"], counts[model]["changed"]),
                (0, 0, 1),
                model,
            )
        self.assertEqual(HpcGroup.objects.get(name="grp-g2").pk, group_pk)
        self.assertEqual(HpcGroup.objects.get(name="grp-g2").gid, 1999)
        self.assertEqual(HpcProject.objects.get(name="proj1").pk, project_pk)
        self.assertEqual(HpcProject.objects.get(name="proj1").gid, 2101)

    def test_missing_group_is_reported_while_users_that_moved_away_are_updated(self):
        s = baseline()
        s.users["dave"]["primary_group"] = "g1"
        del s.groups["g2"]
        out, _ = self.run_import(s)
        self.assertEqual(summary(out)["HpcGroup"]["missing"], 1)
        self.assertEqual(HpcGroup.objects.get(gid=1002).status, OBJECT_STATUS_ACTIVE)
        self.assertEqual(HpcUser.objects.get(username="dave_c").primary_group.gid, 1001)

    def test_missing_group_with_user_moved_to_a_project(self):
        s = baseline()
        s.users["dave"]["primary_group"] = "p1"
        del s.groups["g2"]
        before = self.db_snapshot()
        out, err = self.run_import(s)
        self.assertEqual(self.db_snapshot(), before)
        self.assertEqual(summary(out)["HpcUser"]["missing"], 1)
        self.assertIn("This user will be skipped.", err)

    def test_missing_user_is_reported_and_account_is_not_touched(self):
        s = baseline()
        del s.users["carol"]
        before = self.db_snapshot()
        out, _ = self.run_import(s)
        counts = summary(out)
        self.assertEqual((counts["User"]["missing"], counts["HpcUser"]["missing"]), (1, 1))
        self.assertEqual(self.db_snapshot(), before)
        self.assertEqual(HpcUser.objects.get(username="carol_m").status, OBJECT_STATUS_ACTIVE)
        self.assertTrue(User.objects.get(username="carol@MDC-BERLIN").is_active)

    def test_replacing_a_group_owner_who_is_missing_keeps_group_and_projects(self):
        """alice (owner of g1) disappears and bob takes over g1: nothing cascades."""
        s = baseline()
        del s.users["alice"]
        s.groups["g1"]["owner"] = "bob"
        s.projects["p1"]["members"] = ["bob"]
        self.run_import(s)
        self.assertEqual(HpcUser.objects.get(username="alice_c").status, OBJECT_STATUS_ACTIVE)
        self.assertEqual(HpcGroup.objects.get(gid=1001).owner.username, "bob_c")
        self.assertEqual(HpcGroup.objects.get(gid=1001).status, OBJECT_STATUS_ACTIVE)
        self.assertEqual(HpcProject.objects.get(name="proj1").status, OBJECT_STATUS_ACTIVE)
        self.assertEqual(
            [m.username for m in HpcProject.objects.get(name="proj1").members.all()], ["bob_c"]
        )

    def test_accounts_without_hpc_user_are_never_missing(self):
        User.objects.create(username="standalone@CHARITE")
        User.objects.filter(username="carol@MDC-BERLIN").update(is_staff=True)
        out, _ = self.run_import(baseline())
        self.assertEqual(summary(out)["User"]["missing"], 0)
        self.assertEqual(summary(out)["User"]["initial"], 4)

    def test_deleted_objects_are_reported_missing_and_left_untouched(self):
        HpcUser.objects.filter(username="dave_c").update(status=OBJECT_STATUS_DELETED)
        HpcGroup.objects.filter(gid=1002).update(status=OBJECT_STATUS_DELETED)
        HpcProject.objects.filter(name="proj1").update(status=OBJECT_STATUS_DELETED)
        s = baseline()
        del s.projects["p1"]
        del s.groups["g2"]
        del s.users["dave"]
        before = self.db_snapshot()
        out, err = self.run_import(s)
        counts = summary(out)
        for model, initial in (("User", 4), ("HpcUser", 4), ("HpcGroup", 2), ("HpcProject", 1)):
            self.assertEqual(counts[model]["initial"], initial, model)
            self.assertEqual(counts[model]["missing"], 1, model)
            self.assertEqual(counts[model]["added"], 0, model)
            self.assertEqual(counts[model]["changed"], 0, model)
        self.assertIn("4 records are missing from the state json file.", err)
        self.assertEqual(self.db_snapshot(), before)

    def test_account_and_deleted_hpc_user_are_both_reported_missing(self):
        HpcUser.objects.filter(username="dave_c").update(status=OBJECT_STATUS_DELETED)
        account = User.objects.get(username="dave@CHARITE")
        hpc_user = HpcUser.objects.get(username="dave_c")
        s = baseline()
        del s.users["dave"]
        s.groups["g2"]["owner"] = "alice"
        out, err = self.run_import(s)
        counts = summary(out)
        self.assertEqual(counts["User"]["missing"], 1)
        self.assertEqual(counts["HpcUser"]["missing"], 1)
        self.assertEqual(counts["User"]["initial"], 4)
        self.assertEqual(counts["HpcUser"]["initial"], 4)
        self.assertIn("2 records are missing from the state json file.", err)
        self.assertEqual(User.objects.get(pk=account.pk).is_active, account.is_active)
        hpc_user.refresh_from_db()
        self.assertEqual(hpc_user.status, OBJECT_STATUS_DELETED)
        self.assertEqual(hpc_user.user_id, account.pk)
        self.assertEqual(HpcGroup.objects.get(name="grp-g2").owner.username, "alice_c")

    def test_deleted_objects_are_reactivated_in_place_when_they_reappear(self):
        models = (HpcUser, HpcGroup, HpcProject)
        identities = {
            model: dict(model.objects.values_list("username" if model is HpcUser else "name", "pk"))
            for model in models
        }
        for model in models:
            model.objects.update(status=OBJECT_STATUS_DELETED)
        before = self.db_snapshot()
        candidate = baseline("fresh-export")

        # A dry-run plans updates to retained rows without changing their status.
        out, _ = self.run_import(candidate, write=False)
        self.assertEqual(self.db_snapshot(), before)
        for name, count in (("HpcUser", 4), ("HpcGroup", 2), ("HpcProject", 1)):
            self.assertEqual(summary(out)[name]["added"], 0)
            self.assertEqual(summary(out)[name]["changed"], count)
            self.assertEqual(summary(out)[name]["missing"], 0)

        out, _ = self.run_import(candidate)
        for model in models:
            key = "username" if model is HpcUser else "name"
            self.assertEqual(dict(model.objects.values_list(key, "pk")), identities[model])
            self.assertFalse(model.objects.exclude(status=OBJECT_STATUS_ACTIVE).exists())
            self.assertEqual(summary(out)[model.__name__]["added"], 0)
            self.assertEqual(summary(out)[model.__name__]["changed"], len(identities[model]))

        alice = HpcUser.objects.get(username="alice_c")
        group = HpcGroup.objects.get(name="grp-g1")
        project = HpcProject.objects.get(name="proj1")
        self.assertEqual(alice.primary_group, group)
        self.assertEqual(group.owner, alice)
        self.assertEqual(group.delegate.username, "bob_c")
        self.assertEqual(project.group, group)
        self.assertEqual(project.delegate.username, "bob_c")
        self.assertEqual(
            set(project.members.values_list("username", flat=True)), {"alice_c", "bob_c"}
        )


class TestMalformedInput(ImportCommandTestBase):
    """Bad references are cleared where they occur; skips never cascade.

    Only a user without a usable primary group (a project, or unknown) and a project
    without a group are skipped. A missing owner or delegate becomes None, a missing
    member is dropped.
    """

    def test_missing_group_owner_or_delegate_is_cleared_and_group_is_kept(self):
        for field in ("owner", "delegate"):
            with self.subTest(field=field):
                s = baseline()
                s.groups["g1"][field] = "ghost"
                normalized, err = self.read_state(s)
                self.assertIn(s._id("g1"), normalized.hpc_groups)
                self.assertIsNone(normalized.hpc_groups[s._id("g1")][field])
                self.assertIn(s._id("p1"), normalized.hpc_projects)
                self.assertIn(f"missing {field} reference", err)
                self.assertNotIn("will be skipped", err)

    def test_missing_project_delegate_is_cleared_and_project_is_kept(self):
        s = baseline()
        s.projects["p1"]["delegate"] = "ghost"
        normalized, err = self.read_state(s)
        project = normalized.hpc_projects[s._id("p1")]
        self.assertIsNone(project["delegate"])
        self.assertEqual(len(project["members"]), 2)
        self.assertIn("missing delegate reference", err)

    def test_missing_project_members_are_dropped_and_project_is_kept(self):
        s = baseline()
        s.projects["p1"]["members"] = ["alice", "ghost1", "ghost2"]
        normalized, err = self.read_state(s)
        self.assertEqual(normalized.hpc_projects[s._id("p1")]["members"], [s._id("alice")])
        self.assertIn("missing member reference", err)
        self.assertEqual(err.count("missing member reference"), 1)

    def test_project_with_only_missing_members_is_kept_without_members(self):
        s = baseline()
        s.projects["p1"]["members"] = ["ghost1", "ghost2"]
        normalized, err = self.read_state(s)
        self.assertEqual(normalized.hpc_projects[s._id("p1")]["members"], [])
        self.assertIn("missing member reference", err)

    def test_project_without_group_is_skipped_without_further_warnings(self):
        s = baseline()
        s.projects["p1"].update(group="ghost", delegate="ghost", members=["ghost"])
        normalized, err = self.read_state(s)
        self.assertNotIn(s._id("p1"), normalized.hpc_projects)
        self.assertIn("missing group reference", err)
        self.assertEqual(len(normalized.hpc_groups), 2)
        # nothing else is reported for a project that is gone anyway
        self.assertNotIn("delegate reference", err)
        self.assertNotIn("member reference", err)

    def test_skipped_user_is_cleared_from_references_without_cascading(self):
        """alice owns g1 and is a member of p1; skipping her removes only those references."""
        s = baseline()
        s.users["alice"]["primary_group"] = "ghost"
        normalized, err = self.read_state(s)

        self.assertNotIn(s._id("alice"), normalized.hpc_users)
        self.assertEqual(len(normalized.hpc_users), 3)
        g1 = normalized.hpc_groups[s._id("g1")]
        self.assertIsNone(g1["owner"])
        self.assertEqual(g1["delegate"], s._id("bob"))
        self.assertEqual(len(normalized.hpc_groups), 2)
        p1 = normalized.hpc_projects[s._id("p1")]
        self.assertEqual(p1["members"], [s._id("bob")])
        self.assertEqual(p1["delegate"], s._id("bob"))
        self.assertIn("missing primary_group reference", err)
        self.assertIn("missing owner reference", err)

    def test_skipped_delegate_is_cleared_without_cascading(self):
        s = baseline()
        s.users["bob"]["primary_group"] = "p1"  # a project is not a usable primary group
        normalized, _ = self.read_state(s)
        self.assertNotIn(s._id("bob"), normalized.hpc_users)
        self.assertIsNone(normalized.hpc_groups[s._id("g1")]["delegate"])
        self.assertEqual(normalized.hpc_groups[s._id("g1")]["owner"], s._id("alice"))
        p1 = normalized.hpc_projects[s._id("p1")]
        self.assertIsNone(p1["delegate"])
        self.assertEqual(p1["members"], [s._id("alice")])

    def test_normalized_state_has_no_dangling_references(self):
        s = baseline()
        s.users["alice"]["primary_group"] = "ghost"  # skipped user (owner + member)
        s.users["carol"]["primary_group"] = "p1"  # skipped user
        s.groups["g2"]["delegate"] = "ghost"
        s.projects["p1"]["members"] = ["alice", "bob", "carol", "ghost"]
        s.project("p2", "proj2", gid=2002, group="ghost")  # skipped project
        normalized, _ = self.read_state(s)
        users, groups = normalized.hpc_users, normalized.hpc_groups
        for user in users.values():
            self.assertTrue(user["primary_group"] is None or user["primary_group"] in groups)
        for group in groups.values():
            for role in ("owner", "delegate"):
                self.assertTrue(group[role] is None or group[role] in users)
        for project in normalized.hpc_projects.values():
            self.assertIn(project["group"], groups)
            self.assertTrue(project["delegate"] is None or project["delegate"] in users)
            self.assertTrue(all(member in users for member in project["members"]))

    def test_group_with_missing_owner_is_imported_without_owner(self):
        s = baseline()
        s.groups["g1"]["owner"] = "ghost"
        out, err = self.run_import(s)
        g1 = HpcGroup.objects.get(gid=1001)
        self.assertIsNone(g1.owner)
        self.assertEqual(g1.delegate.username, "bob_c")
        self.assertEqual(HpcUser.objects.count(), 4)
        self.assertEqual(HpcGroup.objects.count(), 2)
        self.assertEqual(HpcProject.objects.get(name="proj1").group, g1)
        self.assertEqual(summary(out)["HpcGroup"]["added"], 2)
        self.assertIn("missing owner reference", err)

    def test_group_owned_by_skipped_user_is_imported_without_owner(self):
        s = baseline()
        s.users["alice"]["primary_group"] = "ghost"
        self.run_import(s)
        self.assertFalse(HpcUser.objects.filter(username="alice_c").exists())
        self.assertIsNone(HpcGroup.objects.get(gid=1001).owner)
        self.assertEqual(HpcProject.objects.get(name="proj1").members.count(), 1)
        self.assertEqual(HpcUser.objects.get(username="bob_c").primary_group.gid, 1001)

    def test_existing_group_keeps_its_owner_when_the_file_owner_is_missing(self):
        self.run_import(baseline())
        before = self.db_snapshot()
        s = baseline()
        s.groups["g1"]["owner"] = "ghost"
        out, _ = self.run_import(s)
        self.assertEqual(self.db_snapshot(), before)
        self.assertEqual(summary(out)["HpcGroup"]["changed"], 0)
        self.assertEqual(HpcGroup.objects.get(gid=1001).owner.username, "alice_c")

    def test_existing_group_with_missing_owner_still_updates_other_fields(self):
        self.run_import(baseline())
        s = baseline()
        s.groups["g1"].update(owner="ghost", description="new", delegate=None)
        out, _ = self.run_import(s)
        g1 = HpcGroup.objects.get(gid=1001)
        self.assertEqual(summary(out)["HpcGroup"]["changed"], 1)
        self.assertEqual(g1.description, "new")
        self.assertEqual(g1.owner.username, "alice_c")  # kept
        self.assertIsNone(g1.delegate)  # the file says there is none
        self.assertEqual(g1.status, OBJECT_STATUS_ACTIVE)

    def test_skipped_owner_does_not_stop_existing_objects_from_updating(self):
        """alice (owner of g1, member of p1) has a malformed primary group in the file."""
        self.run_import(baseline())
        s = baseline()
        s.users["alice"]["primary_group"] = "ghost"
        s.users["bob"]["email"] = "new@example.com"
        s.groups["g1"]["description"] = "new"
        s.projects["p1"]["status"] = "EXPIRED"
        out, err = self.run_import(s)

        counts = summary(out)
        self.assertIn("missing primary_group reference", err)
        self.assertEqual(User.objects.get(username="bob@CHARITE").email, "new@example.com")
        g1 = HpcGroup.objects.get(gid=1001)
        self.assertEqual(g1.description, "new")
        self.assertEqual(g1.owner.username, "alice_c")  # existing owner is kept
        self.assertEqual(g1.delegate.username, "bob_c")
        p1 = HpcProject.objects.get(name="proj1")
        self.assertEqual(p1.status, "EXPIRED")
        self.assertEqual(p1.delegate.username, "bob_c")
        self.assertEqual({m.username for m in p1.members.all()}, {"bob_c"})  # alice dropped
        # Only alice is reported missing; her group and project are neither missing nor added.
        self.assertEqual(counts["HpcUser"]["missing"], 1)
        self.assertEqual((counts["HpcGroup"]["missing"], counts["HpcGroup"]["added"]), (0, 0))
        self.assertEqual((counts["HpcProject"]["missing"], counts["HpcProject"]["added"]), (0, 0))
        self.assertEqual(HpcUser.objects.get(username="alice_c").status, OBJECT_STATUS_ACTIVE)

    def test_skipped_delegate_is_removed_from_existing_objects_only(self):
        self.run_import(baseline())
        s = baseline()
        s.users["bob"]["primary_group"] = "p1"
        self.run_import(s)
        g1 = HpcGroup.objects.get(gid=1001)
        self.assertEqual(g1.owner.username, "alice_c")
        self.assertIsNone(g1.delegate)
        p1 = HpcProject.objects.get(name="proj1")
        self.assertIsNone(p1.delegate)
        self.assertEqual([m.username for m in p1.members.all()], ["alice_c"])
        self.assertEqual(HpcUser.objects.get(username="bob_c").status, OBJECT_STATUS_ACTIVE)

    def test_invalid_project_references(self):
        """group -> project skipped; delegate -> cleared; members -> dropped."""
        for field, value, message in (
            ("group", "ghost", "missing group reference"),
            ("delegate", "ghost", "missing delegate reference"),
            ("members", ["alice", "ghost"], "missing member reference"),
        ):
            with self.subTest(field=field):
                s = baseline()
                s.projects["p1"][field] = value
                _, err = self.run_import(s)
                self.assertEqual(HpcUser.objects.count(), 4)
                self.assertEqual(HpcGroup.objects.count(), 2)
                self.assertIn(message, err)
                if field == "group":
                    self.assertFalse(HpcProject.objects.exists())
                    continue
                project = HpcProject.objects.get(name="proj1")
                if field == "delegate":
                    self.assertIsNone(project.delegate)
                    self.assertEqual(project.members.count(), 2)
                else:
                    self.assertEqual(project.delegate.username, "bob_c")
                    self.assertEqual([m.username for m in project.members.all()], ["alice_c"])
                # reset for the next sub-test
                HpcProject.objects.all().delete()

    def test_duplicate_gids_warn_but_are_retained_in_normalized_input(self):
        # Avoid assuming whether database constraints permit duplicates.
        for collection, key in (("groups", "g2"), ("projects", "p1")):
            with self.subTest(collection=collection):
                s = baseline()
                getattr(s, collection)[key]["gid"] = 1001
                normalized, err = self.read_state(s)
                self.assertEqual(len(normalized.hpc_groups), 2)
                self.assertEqual(len(normalized.hpc_projects), 1)
                self.assertIn("Duplicate gid detected: 1001", err)


class TestCommandBehaviour(ImportCommandTestBase):
    def test_default_dry_run_leaves_database_untouched(self):
        before = self.db_snapshot()
        out, _ = self.run_import(baseline(), write=False)
        self.assertEqual(self.db_snapshot(), before)
        self.assertEqual(summary(out)["HpcUser"]["added"], 4)
        self.assertIn("This was a dry-run.", out)
        self.assertNotIn("Applying changes", out)
        self.assertNotIn("Done.", out)

    def test_write_applies_changes_without_prompting(self):
        out, _ = self.run_import(baseline())
        self.assertEqual(HpcUser.objects.count(), 4)
        self.assertIn("Done.", out)
        self.assertNotIn("This was a dry-run.", out)

    def test_dry_run_reports_updates_and_missing_records_without_writing(self):
        self.run_import(baseline())
        before = self.db_snapshot()
        s = baseline()
        s.users["bob"]["email"] = "new@example.com"
        del s.users["carol"]
        out, err = self.run_import(s, write=False)
        self.assertEqual(self.db_snapshot(), before)
        self.assertEqual(summary(out)["User"]["changed"], 1)
        self.assertEqual(summary(out)["HpcUser"]["missing"], 1)
        self.assertIn("2 records are missing", err)

    def test_report_is_printed_before_writing(self):
        out = StringIO()
        with mock.patch.object(
            User, "save", autospec=True, side_effect=RuntimeError("stop before saving")
        ):
            with self.assertRaisesMessage(RuntimeError, "stop before saving"):
                self.run_import(baseline(), stdout=out)
        out = out.getvalue()
        counts = summary(out)
        self.assertEqual(counts["HpcUser"], {"initial": 0, "added": 4, "missing": 0, "changed": 0})
        self.assertNotIn("Done.", out)

    def test_missing_worker_user_aborts_before_writing(self):
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
        s.users["erin"] = dict(
            s.users["alice"],
            username="erin_c",
            uid=7777,
            primary_group=None,
            email="erin@example.com",
        )
        s.users["bob"]["email"] = "changed@example.com"
        del s.users["carol"]  # missing records are only reported, not written
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


class TestWriteBehaviour(ImportCommandTestBase):
    def test_missing_records_warn_but_do_not_block_changes(self):
        self.run_import(baseline())
        s = baseline()
        del s.users["carol"]
        s.users["bob"]["email"] = "new@example.com"
        out, err = self.run_import(s)
        self.assertEqual(User.objects.get(username="bob@CHARITE").email, "new@example.com")
        self.assertTrue(HpcUser.objects.filter(username="carol_m").exists())
        self.assertIn("2 records are missing from the state json file.", err)
        self.assertNotIn("records are missing", out)
        self.assertIn("Done.", out)

    def test_resources_used_only_changes_are_ignored(self):
        self.run_import(baseline())
        before = self.db_snapshot()
        s = baseline()
        for collection in (s.users, s.groups, s.projects):
            for data in collection.values():
                data["resources_used"] = {key: 999 for key in data["resources_used"]}
        out, _ = self.run_import(s)
        self.assertEqual(self.db_snapshot(), before)
        for counts in summary(out).values():
            self.assertEqual(counts["changed"], 0)

    def test_removed_noinput_option_is_rejected(self):
        with self.assertRaises(CommandError):
            self.run_import(baseline(), "--noinput", write=False)
