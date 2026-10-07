"""Command for importing data from a json file."""

import json
import traceback
from datetime import datetime

from django.contrib import auth
from django.core.management.base import BaseCommand
from django.db import transaction

from adminsec.models import HpcaccessState
from usersec.models import HpcGroup, HpcProject, HpcUser

User = auth.get_user_model()


SUFFIX_MAPPING = {
    "c": "@CHARITE",
    "m": "@MDC-BERLIN",
}


class Command(BaseCommand):
    help = "Import HPC objects from a json file."

    def add_arguments(self, parser):
        parser.add_argument("json", type=str)
        parser.add_argument(
            "-f",
            "--force",
            action="store_true",
            help="Write the changes immediately, without asking for confirmation",
        )

    def read_hpcaccess_state(self, cluster_state):
        """Read and normalize the json file from hpc-access-cli"""
        with open(cluster_state, "r") as jsonfile:
            hpc_state = HpcaccessState(**json.load(jsonfile))
        for _uuid, data in hpc_state.hpc_users.items():
            ldap_user, suffix = data["username"].split("_")
            data["login_name"] = f"{ldap_user}{SUFFIX_MAPPING[suffix]}"
            data["first_name"] = data["first_name"].strip() if data["first_name"] else ""
            data["last_name"] = data["last_name"].strip() if data["last_name"] else ""
            data["name"] = data["full_name"].strip() if data["full_name"] else ""
            data["display_name"] = data["display_name"].strip() if data["display_name"] else ""
            data["phone"] = data["phone_number"]
        return hpc_state

    def users_update_plan(self, cli_import):
        # NOTE: hpc-access user accounts are not removed to avoid wiping out system
        # accounts. GDPR policy for regular user accounts needed?
        usernames = set([data["login_name"] for data in cli_import.hpc_users.values()])
        all = {obj.username: obj for obj in User.objects.filter(username__in=usernames)}
        update = {
            "added": [],  # new objects
            "changed": [],  # tuple of (old, fields) objects
            "removed": User.objects.none(),  # old objects queryset
            "count": User.objects.count(),
        }
        for _uuid, data in cli_import.hpc_users.items():
            old = all.get(data["login_name"])
            if not old:
                new = User(
                    first_name=data["first_name"],
                    last_name=data["last_name"],
                    name=data["name"],
                    display_name=data["display_name"],
                    email=data["email"],
                    is_staff=False,
                    is_superuser=False,
                    is_hpcadmin=False,
                    consented_to_terms=False,  # XXX: this info is not in cluster-state.json
                    phone=data["phone"],
                    username=data["login_name"],
                )
                all[new.username] = new
                update["added"].append(new)
                continue
            # XXX: "consented_to_terms" field is not changed
            changes = {}
            for field in ("first_name", "last_name", "name", "display_name", "email", "phone"):
                if (new_field := data[field]) != getattr(old, field):
                    changes[field] = new_field
            if changes:
                update["changed"].append((old, changes))
        return all, update

    def hpc_users_update_plan(self, cli_import, users):
        usernames = set([data["username"] for data in cli_import.hpc_users.values()])
        all = {obj.username: obj for obj in HpcUser.objects.filter(username__in=usernames)}
        update = {
            "added": [],  # new objects
            "changed": [],  # tuple of (old, changes) objects
            "removed": HpcUser.objects.exclude(username__in=usernames),  # old objects queryset
            "count": HpcUser.objects.count(),
        }
        for uuid, data in cli_import.hpc_users.items():
            ldap_user, suffix = data["username"].split("_")
            login_name = f"{ldap_user}{SUFFIX_MAPPING[suffix]}"
            fk_user = users[login_name]  # XXX Will crash if user is missing
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
                    primary_group=None,
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
            # XXX: The primary_group field here, when it is not None, is just a
            # reference to the group id: the actual primary group will be assigned
            # after the HpcGroup object is created.
            # XXX: In some cases the primary group is actually a project and
            # hpc-access cannot handle this (yet?).
            if data["primary_group"] is None and old.primary_group is not None:
                changes["primary_group"] = None
            elif data["primary_group"] is not None and old.primary_group is None:
                if data["primary_group"] in cli_import.hpc_groups:
                    changes["primary_group"] = cli_import.hpc_groups[data["primary_group"]]["gid"]
                elif data["primary_group"] in cli_import.hpc_projects:
                    primary_group_project_name = cli_import.hpc_projects[data["primary_group"]][
                        "name"
                    ]
                    # changes["primary_group"] = primary_group_project_name
                    changes["primary_group"] = None
                    self.stderr.write(
                        f"Cannot assign project {primary_group_project_name} "
                        f"as primary group for user {data['username']}"
                    )
            elif (
                data["primary_group"] is not None
                and old.primary_group is not None
                and data["primary_group"] in cli_import.hpc_groups
                and cli_import.hpc_groups[data["primary_group"]]["gid"] != old.primary_group.gid
            ):
                changes["primary_group"] = cli_import.hpc_groups[data["primary_group"]]["gid"]
            elif (
                data["primary_group"] is not None
                and old.primary_group is not None
                and data["primary_group"] in cli_import.hpc_projects
                and cli_import.hpc_projects[data["primary_group"]]["gid"] != old.primary_group.gid
            ):
                primary_group_project_name = cli_import.hpc_projects[data["primary_group"]]["name"]
                # changes["primary_group"] = primary_group_project_name
                changes["primary_group"] = None
                self.stderr.write(
                    f"Cannot assign project {primary_group_project_name} "
                    f"as primary group for user {data['username']}"
                )
            # XXX: expiration field is not touched
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
                update["changed"].append((old, changes))
        return all, update

    def hpc_groups_update_plan(self, cli_import, hpc_users):
        gids = set([data["gid"] for data in cli_import.hpc_groups.values()])
        all = {obj.gid: obj for obj in HpcGroup.objects.filter(gid__in=gids)}
        update = {
            "added": [],  # new objects
            "changed": [],  # tuple of (old, changes) objects
            "removed": HpcGroup.objects.exclude(gid__in=gids),  # old objects queryset
            "count": HpcGroup.objects.count(),
        }
        for uuid, data in cli_import.hpc_groups.items():
            # fk_user = users[f"{ldap_user}{SUFFIX_MAPPING[suffix]}"]
            owner_username = cli_import.hpc_users[data["owner"]]["username"]
            fk_owner = hpc_users[owner_username]
            if data["delegate"]:
                delegate_username = cli_import.hpc_users[data["delegate"]]["username"]
                fk_delegate = hpc_users[delegate_username]
            else:
                fk_delegate = None
            old = all.get(data["gid"])
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
                all[new.gid] = new
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
            # XXX: expiration field is not touched
            for field in (
                "name",
                "description",
                "status",
                "gid",
                "folders",
                "resources_requested",
                "resources_used",
            ):
                if (new_field := data[field]) != getattr(old, field):
                    changes[field] = new_field
            if changes:
                update["changed"].append((old, changes))
        return all, update

    def hpc_projects_update_plan(self, cli_import, hpc_users, hpc_groups):
        names = set([data["name"] for data in cli_import.hpc_projects.values()])
        all = {obj.name: obj for obj in HpcProject.objects.filter(name__in=names)}
        update = {
            "added": [],  # tuple of (new, members)
            "changed": [],  # tuple of (old, changes, members) objects
            "removed": HpcProject.objects.exclude(name__in=names),  # old objects queryset
            "count": HpcProject.objects.count(),
        }
        for uuid, data in cli_import.hpc_projects.items():
            group_gid = cli_import.hpc_groups[data["group"]]["gid"]
            fk_group = hpc_groups[group_gid]
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
            if fk_group.gid != old.group.gid:
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
            # XXX: expiration field is not touched
            for field in (
                "gid",
                "folders",
                "status",
                "resources_requested",
                "resources_used",
            ):
                if (new_field := data[field]) != getattr(old, field):
                    changes[field] = new_field
            old_members = set([member.username for member in old.members.all()])
            new_members = set([member.username for member in members])
            if changes or old_members ^ new_members:
                update["changed"].append((old, changes, members))
        return all, update

    def handle(self, *args, **options):
        self.worker_user = User.objects.get(username="hpc-worker")
        with transaction.atomic():
            cli_import = self.read_hpcaccess_state(options["json"])
            users, users_update = self.users_update_plan(cli_import)
            hpc_users, hpc_users_update = self.hpc_users_update_plan(cli_import, users)
            hpc_groups, hpc_groups_update = self.hpc_groups_update_plan(cli_import, hpc_users)
            hpc_projects, hpc_projects_update = self.hpc_projects_update_plan(
                cli_import, hpc_users, hpc_groups
            )

            # Update HpcUser objects with the actual primary group
            for obj in hpc_users_update["added"]:
                primary_group_id = cli_import.hpc_users[obj.uuid]["primary_group"]
                if primary_group_id is None:
                    pass
                elif primary_group_id in cli_import.hpc_groups:
                    primary_group_gid = cli_import.hpc_groups[primary_group_id]["gid"]
                    obj.primary_group = hpc_groups[primary_group_gid]
                elif primary_group_id in cli_import.hpc_projects:
                    # XXX: assigning an HpcProject as primary group is a
                    # TypeError (we could perhaps change the field type but I'm
                    # not sure whether Django knows about unions...)
                    # primary_group_project_name = cli_import.hpc_projects[primary_group_id]["name"]
                    # obj.primary_group = hpc_projects[primary_group_project_name]
                    self.stderr.write(
                        f"Cannot assign project {primary_group_id} "
                        f"as primary group for user {obj.username}"
                    )
                else:
                    self.stderr.write(
                        f"Primary group {primary_group_id} not found for user {obj.username}"
                    )
            for obj, changes in hpc_users_update["changed"]:
                if "primary_group" not in changes or changes["primary_group"] is None:
                    continue
                if changes["primary_group"] in hpc_groups:
                    changes["primary_group"] = hpc_groups[changes["primary_group"]]
                elif changes["primary_group"] in hpc_projects:
                    # XXX: assigning an HpcProject as primary group is a TypeError
                    # changes["primary_group"] = hpc_projects[changes["primary_group"]]
                    self.stderr.write(
                        f"Cannot assign project {changes['primary_group']} "
                        f"as primary group for user {obj.username}"
                    )
                    changes["primary_group"] = None
                else:
                    self.stderr.write(
                        f"Primary group {changes['primary_group']} not found "
                        f"for user {obj.username}"
                    )
                    changes["primary_group"] = None

            self.stdout.write(
                "--- User updates ---\n"
                f" * {users_update['count']} initial objects\n"
                f" * {len(users_update['added'])} added\n"
                f" * {len(users_update['removed'])} removed\n"
                f" * {len(users_update['changed'])} changed\n\n"
                "--- HpcUser updates ---\n"
                f" * {hpc_users_update['count']} initial objects\n"
                f" * {len(hpc_users_update['added'])} added\n"
                f" * {len(hpc_users_update['removed'])} removed\n"
                f" * {len(hpc_users_update['changed'])} changed\n\n"
                "--- HpcGroup updates ---\n"
                f" * {hpc_groups_update['count']} initial objects\n"
                f" * {len(hpc_groups_update['added'])} added\n"
                f" * {len(hpc_groups_update['removed'])} removed\n"
                f" * {len(hpc_groups_update['changed'])} changed\n\n"
                "--- HpcProject updates ---\n"
                f" * {hpc_projects_update['count']} initial objects\n"
                f" * {len(hpc_projects_update['added'])} added\n"
                f" * {len(hpc_projects_update['removed'])} removed\n"
                f" * {len(hpc_projects_update['changed'])} changed\n\n"
            )

            if not options["force"]:
                ans = input("Do you want to proceed? [Y/n]: ")
                if ans and not ans.lower().startswith("y"):
                    self.stdout.write("The database was not changed, bye for now.")
                    return

            try:
                # Write to the db
                self.stdout.write("Applying changes to the database, please be patient...")
                for new in users_update["added"]:
                    new.save()
                for old, changes in users_update["changed"]:
                    for field, value in changes.items():
                        setattr(old, field, value)
                    old.save()

                for new in hpc_users_update["added"]:
                    pg = new.primary_group
                    new.primary_group = None
                    new.save_with_version()
                    new.primary_group = pg
                for old, changes in hpc_users_update["changed"]:
                    if "primary_group" in changes:
                        pg = changes["primary_group"]
                        changes["primary_group"] = None
                        old.update_with_version(**changes)
                        old.primary_group = pg
                    else:
                        old.update_with_version(**changes)

                for new in hpc_groups_update["added"]:
                    new.save_with_version()
                for old, changes in hpc_groups_update["changed"]:
                    old.update_with_version(**changes)

                # Save users again to apply the primary_group changes
                for new in hpc_users_update["added"]:
                    new.save()
                for old, _changes in hpc_users_update["changed"]:
                    old.save()

                for new, members in hpc_projects_update["added"]:
                    new.save_with_version()
                    for member in members:
                        new.members.add(member)
                for old, changes, members in hpc_projects_update["changed"]:
                    old.update_with_version(**changes)
                    old.members.clear()
                    for member in members:
                        old.members.add(member)

                # Delete objects at the end and in reverse order to avoid
                # side effects of cascade-deletion.
                hpc_projects_update["removed"].delete()
                hpc_groups_update["removed"].delete()
                hpc_users_update["removed"].delete()
                users_update["removed"].delete()

                self.stdout.write("Done.")

            except Exception as ex:
                self.stderr.write(f"Transaction aborted due to {type(ex).__name__}: {ex}")
                self.stderr.write(traceback.format_exc())
                raise ex
