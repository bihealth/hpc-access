"""Command for importing data from a json file."""

import json
import traceback
from datetime import datetime

from django.contrib import auth
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Count

from adminsec.models import HpcaccessState
from usersec.models import OBJECT_STATUS_DELETED, HpcGroup, HpcProject, HpcUser

User = auth.get_user_model()


SUFFIX_MAPPING = {
    "c": "@CHARITE",
    "m": "@MDC-BERLIN",
}


class Command(BaseCommand):
    help = "Import HPC objects from a json file."

    def _read_hpcaccess_state(self, cluster_state):
        """Read and normalize the json file from hpc-access-cli"""
        with open(cluster_state, "r") as jsonfile:
            hpc_state = HpcaccessState(**json.load(jsonfile))
        for data in hpc_state.hpc_users.values():
            ldap_user, suffix = data["username"].split("_")
            data["login_name"] = f"{ldap_user}{SUFFIX_MAPPING[suffix]}"
            data["first_name"] = data["first_name"].strip() if data["first_name"] else ""
            data["last_name"] = data["last_name"].strip() if data["last_name"] else ""
            data["name"] = data["full_name"].strip() if data["full_name"] else ""
            data["display_name"] = data["display_name"].strip() if data["display_name"] else ""
            data["phone"] = data["phone_number"]
            if primary_group := data["primary_group"]:
                if primary_group in hpc_state.hpc_projects:
                    self.stderr.write(
                        f"Warning: primary_group {primary_group} for user {data['name']} "
                        "is a project and will be set to NULL."
                    )
                elif primary_group not in hpc_state.hpc_groups:
                    raise CommandError(
                        "Malformed input: missing primary_group reference "
                        f"({data['primary_group']}) for user {data['username']}"
                    )
        all_gids = set()
        for data in hpc_state.hpc_groups.values():
            if data["owner"] not in hpc_state.hpc_users:
                raise CommandError(
                    "Malformed input: missing owner reference "
                    f"({data['owner']}) for group {data['name']}"
                )
            if data["delegate"] and data["delegate"] not in hpc_state.hpc_users:
                raise CommandError(
                    "Malformed input: missing delegate reference "
                    f"({data['delegate']}) for group {data['name']}"
                )
            if data["gid"] in all_gids:
                raise CommandError(f"Duplicate gid detected: {data['gid']}")
            all_gids.add(data["gid"])
        for data in hpc_state.hpc_projects.values():
            if data["group"] not in hpc_state.hpc_groups:
                raise CommandError(
                    "Malformed input: missing group reference "
                    f"({data['group']}) for project {data['name']}"
                )
            if data["delegate"] and data["delegate"] not in hpc_state.hpc_users:
                raise CommandError(
                    "Malformed input: missing delegate reference "
                    f"({data['delegate']}) for project {data['name']}"
                )
            for member_uuid in data["members"]:
                if member_uuid not in hpc_state.hpc_users:
                    raise CommandError(
                        "Malformed input: missing member reference "
                        f"({member_uuid}) for project {data['name']}"
                    )
            if data["gid"] in all_gids:
                raise CommandError(f"Duplicate gid detected: {data['gid']}")
            all_gids.add(data["gid"])

        return hpc_state

    def _users_update_plan(self, cli_import):
        usernames = {data["login_name"] for data in cli_import.hpc_users.values()}
        all = {obj.username: obj for obj in User.objects.filter(username__in=usernames)}
        existing = User.objects.annotate(hpcuser_count=Count("hpcuser_user")).exclude(
            hpcuser_count=0
        )
        update = {
            # new objects
            "added": [],
            # tuple of (old, updated_fields) objects
            "changed": [],
            # queryset of old objects that are missing from the imported file
            "missing": existing.exclude(username__in=usernames),
            # count of existing and active objects
            "count": existing.count(),
        }
        for _uuid, data in cli_import.hpc_users.items():
            old = all.get(data["login_name"])
            if not old:
                # XXX: how are new users created right now? and how is their password chosen?
                # Does it make sense to create them here?
                new = User(
                    first_name=data["first_name"],
                    last_name=data["last_name"],
                    name=data["name"],
                    display_name=data["display_name"],
                    email=data["email"],
                    is_staff=False,
                    is_superuser=False,
                    is_hpcadmin=False,
                    # XXX: this info is not in the imported file: what should the default be?
                    consented_to_terms=False,
                    phone=data["phone"],
                    username=data["login_name"],
                )
                all[new.username] = new
                update["added"].append(new)
                continue
            changes = {}
            for field in ("first_name", "last_name", "name", "display_name", "email", "phone"):
                if (new_field := data[field]) != getattr(old, field):
                    changes[field] = new_field
            if changes:
                if not old.is_active:
                    self.stderr.write(
                        f'Warning: user "{old.username}" is not active, but their data changed.'
                    )
                update["changed"].append((old, changes))
        return all, update

    def _hpc_users_update_plan(self, cli_import, users):
        usernames = {data["username"] for data in cli_import.hpc_users.values()}
        all = {obj.username: obj for obj in HpcUser.objects.filter(username__in=usernames)}
        existing = HpcUser.objects.exclude(status=OBJECT_STATUS_DELETED)
        update = {
            "added": [],
            "changed": [],
            "missing": existing.exclude(username__in=usernames),
            "count": existing.count(),
        }
        for uuid, data in cli_import.hpc_users.items():
            fk_user = users.get(data["login_name"])
            if not fk_user:
                self.stderr.write(
                    f'Error: HpcUser "{data["username"]}" does not have an associated User account.'
                )
                raise KeyError(data["login_name"])
            if data["primary_group"]:
                if data["primary_group"] in cli_import.hpc_groups:
                    primary_group_name = cli_import.hpc_groups[data["primary_group"]]["name"]
                elif data["primary_group"] in cli_import.hpc_projects:
                    primary_group_name = cli_import.hpc_projects[data["primary_group"]]["name"]
                else:
                    # This should never happen because we check for missing references
                    # in _read_hpcaccess_state()
                    self.stderr.write(
                        f"Error: Primary group {data['primary_group']} not found "
                        f"for user {data['username']}"
                    )
                    raise KeyError(data["primary_group"])
            else:
                primary_group_name = None
            old = all.get(data["username"])
            if not old:
                new = HpcUser(
                    uuid=uuid,
                    user=fk_user,
                    resources_requested=data["resources_requested"],
                    resources_used=data["resources_used"],
                    creator=self.worker_user,
                    status=data["status"],
                    home_directory=data["home_directory"],
                    primary_group=HpcGroup(name=primary_group_name),
                    expiration=datetime.fromisoformat(data["expiration"]),
                    login_shell=data["login_shell"],
                    username=data["username"],
                    uid=data["uid"],
                )
                all[new.username] = new
                update["added"].append(new)
                continue
            changes = {}
            if data["login_name"] != old.user.username:
                changes["user"] = fk_user
            if (
                old.primary_group
                and old.primary_group.name != primary_group_name
                or not old.primary_group
                and primary_group_name
            ):
                changes["primary_group"] = primary_group_name
            for field in (
                "resources_requested",
                "resources_used",
                "status",
                "home_directory",
                "login_shell",
                "uid",
            ):
                if (new_field := data[field]) != getattr(old, field):
                    changes[field] = new_field
            if changes:
                if not old.user.is_active:
                    self.stderr.write(
                        f'Warning: the user associated with "{old.username}" is not active, '
                        "but their Hpc data changed."
                    )
                update["changed"].append((old, changes))
        return all, update

    def _hpc_groups_update_plan(self, cli_import, hpc_users):
        names = {data["name"] for data in cli_import.hpc_groups.values()}
        all = {obj.name: obj for obj in HpcGroup.objects.filter(name__in=names)}
        existing = HpcGroup.objects.exclude(status=OBJECT_STATUS_DELETED)
        update = {
            "added": [],
            # tuple of (old, changed_fields, members)
            "changed": [],
            "missing": existing.exclude(name__in=names),
            "count": existing.count(),
        }
        for uuid, data in cli_import.hpc_groups.items():
            owner_username = cli_import.hpc_users[data["owner"]]["username"]
            fk_owner = hpc_users.get(owner_username)
            if data["delegate"]:
                delegate_username = cli_import.hpc_users[data["delegate"]]["username"]
                fk_delegate = hpc_users[delegate_username]
            else:
                fk_delegate = None
            old = all.get(data["name"])
            if not old:
                new = HpcGroup(
                    uuid=uuid,
                    name=data["name"],
                    description=data["description"],
                    creator=self.worker_user,
                    owner=fk_owner,
                    delegate=fk_delegate,
                    status=data["status"],
                    gid=data["gid"],
                    folders=data["folders"],
                    resources_requested=data["resources_requested"],
                    resources_used=data["resources_used"],
                    expiration=datetime.fromisoformat(data["expiration"]),
                )
                all[new.name] = new
                update["added"].append(new)
                continue
            changes = {}
            if fk_owner.username != old.owner.username:
                changes["owner"] = fk_owner
            if (
                fk_delegate is not None
                and old.delegate is None
                or fk_delegate is None
                and old.delegate is not None
                or fk_delegate is not None
                and old.delegate is not None
                and fk_delegate.username != old.delegate.username
            ):
                changes["delegate"] = fk_delegate
            for field in (
                "gid",
                "description",
                "status",
                "folders",
                "resources_requested",
                "resources_used",
            ):
                if (new_field := data[field]) != getattr(old, field):
                    changes[field] = new_field
            if changes:
                update["changed"].append((old, changes))
        return all, update

    def _hpc_projects_update_plan(self, cli_import, hpc_users, hpc_groups):
        names = {data["name"] for data in cli_import.hpc_projects.values()}
        all = {obj.name: obj for obj in HpcProject.objects.filter(name__in=names)}
        existing = HpcProject.objects.exclude(status=OBJECT_STATUS_DELETED)
        update = {
            "added": [],
            "changed": [],
            "missing": existing.exclude(name__in=names),
            "count": existing.count(),
        }
        for uuid, data in cli_import.hpc_projects.items():
            group_name = cli_import.hpc_groups[data["group"]]["name"]
            fk_group = hpc_groups[group_name]
            if data["delegate"]:
                delegate_username = cli_import.hpc_users[data["delegate"]]["username"]
                fk_delegate = hpc_users[delegate_username]
            else:
                fk_delegate = None
            members = []
            for member_uuid in data["members"]:
                fk_member = hpc_users[cli_import.hpc_users[member_uuid]["username"]]
                members.append(fk_member)
            old = all.get(data["name"])
            if not old:
                new = HpcProject(
                    uuid=uuid,
                    name=data["name"],
                    gid=data["gid"],
                    folders=dict(data["folders"]),
                    status=data["status"],
                    creator=self.worker_user,
                    group=fk_group,
                    delegate=fk_delegate,
                    resources_requested=dict(data["resources_requested"]),
                    resources_used=dict(data["resources_used"]),
                    expiration=datetime.fromisoformat(data["expiration"]),
                )
                all[new.name] = new
                update["added"].append((new, members))
                continue
            changes = {}
            if fk_group.name != old.group.name:
                changes["group"] = fk_group
            if (
                fk_delegate is not None
                and old.delegate is None
                or fk_delegate is None
                and old.delegate is not None
                or fk_delegate is not None
                and old.delegate is not None
                and fk_delegate.username != old.delegate.username
            ):
                changes["delegate"] = fk_delegate
            for field in (
                "gid",
                "folders",
                "status",
                "resources_requested",
                "resources_used",
            ):
                if (new_field := data[field]) != getattr(old, field):
                    changes[field] = new_field
            old_members = {member.username for member in old.members.all()}
            new_members = {member.username for member in members}
            if changes or old_members ^ new_members:
                update["changed"].append((old, changes, members))
        return all, update

    def add_arguments(self, parser):
        parser.add_argument("state_json_file", type=str)
        parser.add_argument(
            "--no-input",
            "--noinput",
            action="store_true",
            help="Do NOT prompt for confirmation, write the changes immediately.",
        )

    def handle(self, *args, **options):
        self.worker_user = User.objects.get(username="hpc-worker")
        with transaction.atomic():
            cli_import = self._read_hpcaccess_state(options["state_json_file"])
            users, users_update = self._users_update_plan(cli_import)
            hpc_users, hpc_users_update = self._hpc_users_update_plan(cli_import, users)
            hpc_groups, hpc_groups_update = self._hpc_groups_update_plan(cli_import, hpc_users)
            hpc_projects, hpc_projects_update = self._hpc_projects_update_plan(
                cli_import, hpc_users, hpc_groups
            )

            missing_entries = 0
            for title, update in [
                ("User", users_update),
                ("HpcUser", hpc_users_update),
                ("HpcGroup", hpc_groups_update),
                ("HpcProject", hpc_projects_update),
            ]:
                missing_entries += len(update["missing"])
                self.stdout.write(
                    f"--- {title} updates ---\n"
                    f" * {update['count']} initial objects\n"
                    f" * {len(update['added'])} added\n"
                    f" * {len(update['missing'])} missing\n"
                    f" * {len(update['changed'])} changed\n\n"
                )
            self.stdout.write(f"{missing_entries} records are missing from the state json file.")
            # XXX: should we print more information? e.g. the usernames that are added/missing?

            if not options["noinput"]:
                ans = input("Do you want to proceed? [y/N]: ")
                if not ans or not ans.lower().startswith("y"):
                    self.stdout.write("The database was not changed, bye for now.")
                    return
            elif missing_entries:
                self.stderr.write(
                    "Some entries were missing from the state json file. "
                    "--no-input cannot be used under these circumstance. Aborting..."
                )
                raise CommandError("Missing entries")

            try:
                self.stdout.write("Applying changes to the database, please be patient...")

                for new in users_update["added"]:
                    new.save()

                for new in hpc_users_update["added"]:
                    pg = new.primary_group
                    new.primary_group = None
                    new.save()
                    new.primary_group = pg

                for new in hpc_groups_update["added"]:
                    new.save()

                # Save the hpc_users again now that the primary_group objects exist
                for new in hpc_users_update["added"]:
                    new.primary_group = hpc_groups.get(new.primary_group.name)
                    new.save()

                for old, changes in (
                    users_update["changed"]
                    + hpc_users_update["changed"]
                    + hpc_groups_update["changed"]
                ):
                    for field, value in changes.items():
                        if field == "primary_group":
                            value = hpc_groups.get(value)
                        setattr(old, field, value)
                    old.save()

                for new, members in hpc_projects_update["added"]:
                    new.save()
                    for member in members:
                        new.members.add(member)

                for old, changes, members in hpc_projects_update["changed"]:
                    for field, value in changes.items():
                        setattr(old, field, value)
                    old.save()
                    old.members.set(members)

                self.stdout.write("Done.")

            except Exception as ex:
                self.stderr.write(f"Transaction will be aborted due to {type(ex).__name__}: {ex}")
                self.stderr.write(traceback.format_exc())
                raise
